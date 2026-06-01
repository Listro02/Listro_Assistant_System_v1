from functools import wraps
from string import Template
from datetime import datetime
import json
import os
from pathlib import Path

from core.config import XMemoryConfig
from core.database.sqlite_store import RawMessageStore
from core.database.vector_store import VectorStore
from core.embedding import EmbeddingClient
from core.consolidator.pipeline import ConsolidationPipeline
from core.retriever.search import MemoryRetriever
from core.sliding_window import SlidingWindow
from core.utils.openai_client import OpenAIClient
from core.utils.log_utils import log_set, log_jsonl
from core.utils.json_utils import extract_json_from_llm_response

LAS_log = log_set("XMemoryLAS")
log = log_jsonl()

def input_record(func):
    """L0 SQLite (RawMessageStore)에 사용자 발언을 기록하는 데코레이터"""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        # 1. 턴 기록 전에 사용자 발언을 L0와 윈도우에 삽입
        name = kwargs.get("name", "Unknown")
        content = kwargs.get("content", "")
        
        # SQLite L0 저장
        turn_id = self.sqlite_store.insert_turn(speaker="user", name=name, content=content)
        
        # Sliding Window 추가
        turn_data = {"role": "user", "name": name, "content": content, "turn_id": turn_id, "timestamp": datetime.now().isoformat()}
        evicted = self.window.push(turn_data)
        
        # Evict 발생 시 비동기 통합 트리거
        if evicted:
            # 윈도우에서 쫓겨난 턴이 있을 때, 해당 턴들을 통합 큐로 전달
            # L.A.S.의 설계상 evict_turns 하나당 트리거하기보다는 모아서 할 수 있지만 여기선 단순 구현
            start_turn = evicted[0]["turn_id"]
            end_turn = evicted[-1]["turn_id"]
            self.consolidator.trigger(start_turn, end_turn)
            
        LAS_log.sys_log.info(f"사용자 '{name}'의 입력 L0 기록 및 Window PUSH (Turn ID: {turn_id})")

        # 2. 본 함수(talking_LAS) 실행
        result = func(self, *args, **kwargs)
        
        # 3. AI 응답을 L0와 윈도우에 삽입
        ai_turn_id = self.sqlite_store.insert_turn(speaker="assistant", name="L.A.S.", content=result)
        ai_turn_data = {"role": "assistant", "name": "L.A.S.", "content": result, "turn_id": ai_turn_id, "timestamp": datetime.now().isoformat()}
        
        ai_evicted = self.window.push(ai_turn_data)
        if ai_evicted:
            start_turn = ai_evicted[0]["turn_id"]
            end_turn = ai_evicted[-1]["turn_id"]
            self.consolidator.trigger(start_turn, end_turn)
            
        LAS_log.sys_log.info(f"AI 응답 L0 기록 및 Window PUSH (Turn ID: {ai_turn_id})")
            
        return result
    return wrapper

class XMemoryLAS:
    """
    기존 LAS_SYSTEM 구조를 계승한 xMemory 기반 대화 시스템.
    MODULE/LAS.py의 LAS_SYSTEM을 포크하여 메모리/판단 부분을 교체.
    """
    def __init__(self, config: XMemoryConfig = None):
        self.config = config if config else XMemoryConfig()
        self.AI = OpenAIClient()
        self.place = "Listro의 개발실"
        self.scenario = "당신은 'Listro의 개발실'에서 당신의 ai비서로써의 역할을 수행하는지 테스트하고 있습니다."

        # 기존 프롬프트 로딩 유지
        try:
            with open(self.config.role_prompt_path, 'r', encoding='utf-8') as f:
                self.role_prompt = f.read()
        except:
            self.role_prompt = "You are L.A.S., an AI assistant."
            
        try:
            with open(self.config.judge_prompt_path, 'r', encoding='utf-8') as f:
                self.judge_prompt = f.read()
        except:
            self.judge_prompt = "Classify the user intent into [일반_대화], [음악_재생], [판단_불가]."
            
        self.reference = ""
        try:
            with open(self.config.reference_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()[-20:]
                for line in lines:
                    data = json.loads(line)
                    self.reference += f"Listro: {data.get('user', '')}\nL.A.S.: {data.get('assistant', '')}\n"
        except:
            pass

        # ── 신규 xMemory 컴포넌트 (교체 부분) ──
        self.window = SlidingWindow(max_size=self.config.window_size, overlap=self.config.overlap_size)
        self.sqlite_store = RawMessageStore(self.config.sqlite_path)
        self.vector_store = VectorStore(self.config.vector_store_dir)
        
        self.embedding = EmbeddingClient(self.AI, model=self.config.embedding_model)
        
        # Load themes on startup
        self._init_themes()
        
        self.consolidator = ConsolidationPipeline(self.config, self.sqlite_store, self.vector_store, self.embedding, self.AI)
        self.retriever = MemoryRetriever(self.config, self.vector_store, self.sqlite_store, self.embedding)
        
        self.dic_ai = {"role" : "assistant", "name" : "L.A.S.", "content" : None}

    def _init_themes(self):
        try:
            with open(self.config.themes_path, 'r', encoding='utf-8') as f:
                themes = json.load(f)
            
            # DB에 테마가 없는 경우에만 임베딩 후 삽입 (API 호출 비용 절약)
            if self.vector_store.themes.count() == 0:
                LAS_log.sys_log.info(f"테마 데이터베이스가 비어 있습니다. {len(themes)}개의 테마를 임베딩합니다...")
                texts_to_embed = [t["name"] + ": " + t.get("summary", "") for t in themes]
                embeddings = self.embedding.embed_batch(texts_to_embed)
                self.vector_store.init_themes(themes, embeddings)
            else:
                LAS_log.sys_log.info(f"테마 데이터베이스 이미 존재: {self.vector_store.themes.count()}개")
                
        except Exception as e:
            LAS_log.sys_log.error(f"테마 초기화 실패: {e}")

    def record(self, data):
        """log 기록 method (기존 유지)"""
        # xMemory에서는 파일 경로를 XMemoryConfig에서 가져오거나 로그 폴더를 사용
        log_path = Path(self.config.data_dir) / "logs" / "LAS_talking_history.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        log_data = {"timestamp": f"{datetime.now()}", "level": "Info", "used_method": ""}
        log_data.update(data)
        log.append_to_jsonl(log_path, log_data)
        LAS_log.sys_log.info(f"✅ record 메서드를 통해 XMemoryLAS.py 기록됨.")

    def judge(self, content: str, need_rag_check: bool = True):
        """기존 judge() 확장: RAG 필요 여부 판별 추가"""
        LAS_log.sys_log.info("judge 메서드 사용됨.")
        messages = [
            {"role": "system", "content": self.judge_prompt},
            {"role": "system", "content": "RAG 검색이 필요한 구체적인 정보 요청이나 과거 맥락 질문이면 [RAG_필요]를, 단순 리액션이나 인사면 [NO_RAG]를 추가로 판단하세요."}
        ]
        
        prompt = f"사용자 입력 : {content}"
        result = self.AI.call_AI(prompt, "LAS", not_file=messages, model_set=self.config.judge_model, goal="Judge")
        
        data = {"used_method": "judge", "result(judge)": result}
        self.record(data)
        return result

    @input_record
    def talking_LAS(self, *, name: str = None, content: str = None, memory_context: dict = None, support_list: list = [], example: list = []):
        """기존 talking_LAS() 확장: Tool Calling + 메모리 주입"""
        LAS_log.sys_log.info("talking_LAS 메서드 사용됨.")

        if name != None:
            formatted_content = f"{name}: " + content 
        else:
            formatted_content = content

        messages = Template(self.role_prompt)
        
        # xMemory: L2 사실 + L1 목차 주입
        memory_injection = {"facts": []}
        user_memory_injection = {"facts": []}
        
        if memory_context:
            if memory_context.get("facts"):
                memory_injection["facts"] = [f["text"] for f in memory_context["facts"]]
            if memory_context.get("episodes"):
                memory_injection["episodes"] = [e["summary"] for e in memory_context["episodes"]]
            if memory_context.get("user_facts"):
                user_memory_injection["facts"] = [f["text"] for f in memory_context["user_facts"]]

        substitutions = {
            'REFERENCE': self.reference,
            'MEMORY': memory_injection,
            'USER_MEMORY': user_memory_injection,
            'SCENARIO': self.scenario,
            'PLACE': self.place
        }
        for i in support_list:
            substitutions.update(i)
            
        sys_prompt = messages.safe_substitute(substitutions)
        
        chat_messages = [{"role": "system", "content": sys_prompt}]
        chat_messages += example
        chat_messages += [{"role": "user", "content": formatted_content}]

        # Tool calling 설정 (Deep Search)
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "deep_search",
                    "description": "에피소드의 원본 대화 내용을 검색합니다. 에피소드 ID를 사용하여 검색합니다.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "episode_id": {
                                "type": "string",
                                "description": "조회할 에피소드 ID (예: E_123)"
                            }
                        },
                        "required": ["episode_id"]
                    }
                }
            }
        ]

        # 1차 생성
        response_data = self.AI.call_AI_with_tools(chat_messages, tools=tools, model_set=self.config.main_model)
        
        # Tool Call 처리 (Phase 4)
        if response_data["type"] == "tool_call":
            tool_calls = response_data["tool_calls"]
            message = response_data["message"]
            chat_messages.append(message)
            
            for tool_call in tool_calls:
                if tool_call.function.name == "deep_search":
                    args = json.loads(tool_call.function.arguments)
                    episode_id = args.get("episode_id")
                    
                    # 딥 서치 실행
                    search_result = self.retriever.deep_search(episode_id)
                    
                    # 결과 추가
                    chat_messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": "deep_search",
                        "content": search_result
                    })
            
            # 2차 생성
            final_response = self.AI.call_AI_with_tools(chat_messages, model_set=self.config.main_model)
            final_content = final_response.get("content", "오류 발생")
        else:
            final_content = response_data.get("content", "오류 발생")

        if "</thinking>" in final_content:
            final_content = final_content.split("</thinking>")[1].strip()

        self.dic_ai["content"] = final_content
        data = {"used_method": "talking_LAS", "response": final_content}
        self.record(data)

        return final_content

    def process(self, content: str, talker: str = None) -> str:
        """
        기존 process() 골격을 유지하되 내부 호출 교체.
        """
        if talker == "listro02":
            talker = "Listro"
            
        # 1. RAG 필요 여부 판별 (judge)
        judge_result = self.judge(content)
        need_rag = "NO_RAG" not in judge_result
        
        # 2. 기억 검색 (Retrieve)
        memory_context = self.retriever.retrieve(content, need_rag=need_rag)
        
        support = [{"USER_NAME": talker}]
        if "[음악_재생]" in judge_result:
            support.append({"role": "system", "content": "사용 가능 기능 : 음악 재생"})
            
        # 3. 단기 기억(윈도우) 로드
        history = self.window.get_messages()
        
        # 4. 응답 생성 (talking_LAS - 내부에서 윈도우 push 및 trigger 수행)
        result = self.talking_LAS(
            name=talker, 
            content=content, 
            memory_context=memory_context, 
            support_list=support, 
            example=history
        )
        
        return result
