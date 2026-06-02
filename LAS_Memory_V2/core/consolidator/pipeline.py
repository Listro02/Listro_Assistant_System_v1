import time
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from core.config import XMemoryConfig
from core.database.sqlite_store import RawMessageStore
from core.database.vector_store import VectorStore
from core.embedding import EmbeddingClient
from core.utils.openai_client import OpenAIClient
from core.utils.log_utils import log_set
from core.utils.json_utils import extract_json_from_llm_response
from core.consolidator.extractor import FactExtractor
from core.consolidator.context_builder import ContextBuilder

pipe_log = log_set("ConsolidationPipeline")

class ConsolidationPipeline:
    """4-Phase 비동기 통합 파이프라인"""
    def __init__(self, config: XMemoryConfig, sqlite_store: RawMessageStore, 
                 vector_store: VectorStore, embedding_client: EmbeddingClient, 
                 openai_client: OpenAIClient):
        self.config = config
        self.sqlite = sqlite_store
        self.vector = vector_store
        self.embedding = embedding_client
        self.openai = openai_client
        
        self.extractor = FactExtractor(self.openai, self.config.prompts_dir + "/fact_extract_prompt.txt", model=self.config.extraction_model)
        self.context_builder = ContextBuilder(self.openai, self.config.prompts_dir + "/context_generate_prompt.txt", model=self.config.extraction_model)
        
        # 충돌 검증용 프롬프트 로드
        with open(Path(self.config.prompts_dir) / "conflict_check_prompt.txt", 'r', encoding='utf-8') as f:
            self.conflict_prompt = f.read()
            
        self._executor = ThreadPoolExecutor(max_workers=self.config.consolidation_workers)
        self._lock = threading.Lock()
        
    def trigger(self, start_turn: int, end_turn: int):
        """
        비동기 실행 트리거: L0 기록 -> WAL 등록 -> 백그라운드 파이프라인.
        이 메서드는 메인 스레드에서 즉시 반환되어야 함.
        """
        wal_id = self.sqlite.enqueue_wal(start_turn, end_turn)
        pipe_log.sys_log.info(f"WAL 등록 완료: ID={wal_id}, Range={start_turn}~{end_turn}")
        
        # 스레드 풀에 작업 제출
        self._executor.submit(self._process_next_wal)
        
    def _process_next_wal(self):
        """WAL 큐에서 하나를 꺼내 파이프라인 실행"""
        # 스레드 동시 접근 제어
        with self._lock:
            wal_entry = self.sqlite.dequeue_wal()
            
        if not wal_entry:
            return
            
        wal_id = wal_entry['id']
        try:
            self._run_pipeline(wal_entry)
            self.sqlite.complete_wal(wal_id)
            pipe_log.sys_log.info(f"WAL 작업 완료: ID={wal_id}")
        except Exception as e:
            self.sqlite.fail_wal(wal_id)
            pipe_log.sys_log.error(f"WAL 작업 실패: ID={wal_id}, Error={e}")
            
    def _run_pipeline(self, wal_entry: dict):
        start_turn = wal_entry['start_turn']
        end_turn = wal_entry['end_turn']
        created_at = wal_entry['created_at']
        
        # 0. 데이터 준비
        chunk = self.sqlite.get_turns_by_range(start_turn, end_turn)
        if not chunk:
            raise ValueError("해당 범위의 대화 데이터가 없습니다.")
            
        # 1. Phase 2: Pass 1 (사실 추출)
        extracted_fact_texts = self.extractor.extract(chunk)
        pipe_log.sys_log.info(f"사실 추출 완료: {len(extracted_fact_texts)}개")
        
        # 2. Phase 2: Pass 2 (맥락 생성)
        context_data = self.context_builder.build(chunk, extracted_fact_texts)
        pipe_log.sys_log.info(f"맥락 생성 완료: {context_data['summary'][:30]}...")
        
        # 에피소드 ID 생성
        episode_id = f"E_{start_turn}"
        
        # 3. Phase 3 & 3.5: 사실 처리 및 충돌 감지
        final_facts = []
        if extracted_fact_texts:
            fact_embeddings = self.embedding.embed_batch(extracted_fact_texts)
            
            for text, emb in zip(extracted_fact_texts, fact_embeddings):
                fact_id = f"F_{uuid.uuid4().hex[:8]}"
                
                # 3.5 충돌 감지
                candidates = self.vector.find_conflicting_facts(emb, threshold=self.config.conflict_threshold)
                
                status = "active"
                # 충돌 후보군이 있으면 LLM으로 평가
                for cand in candidates:
                    verdict = self._detect_and_resolve_conflicts(text, cand, created_at)
                    if verdict == "supersede":
                        self.vector.supersede_fact(cand["id"], fact_id)
                        pipe_log.sys_log.info(f"사실 갱신: {cand['id']} -> {fact_id}")
                
                final_facts.append({
                    "id": fact_id,
                    "text": text,
                    "embedding": emb,
                    "source_episode_id": episode_id,
                    "source_range_start": start_turn,
                    "source_range_end": end_turn,
                    "created_at": created_at,
                    "status": status
                })
        
        # 4. 에피소드 임베딩 및 독립적 테마 매핑 (Phase 4)
        episode_text_to_embed = context_data["summary"] + " " + " ".join(context_data["topics"])
        episode_embedding = self.embedding.embed_text(episode_text_to_embed)
        
        episode = {
            "id": episode_id,
            "summary": context_data["summary"],
            "parent_theme_id": "", # L3 -> L2 -> L1 아키텍처에 따라 에피소드 단위 강제 테마 할당 제거
            "target_range_start": start_turn,
            "target_range_end": end_turn,
            "topics": context_data["topics"],
            "tech_stack": context_data["tech_stack"],
            "conclusion": context_data["conclusion"],
            "extracted_facts": [f["id"] for f in final_facts],
            "created_at": created_at
        }
        
        # Vector Store에 일괄 저장
        if final_facts:
            facts_to_add = []
            embs_to_add = []
            for f in final_facts:
                fact_dict = f.copy()
                
                # 각 사실 노드별로 독립적 테마 매핑 (L3 매핑)
                fact_matched_themes = self.vector.find_themes(fact_dict["embedding"], threshold=self.config.theme_threshold)
                fact_dict["parent_theme_id"] = fact_matched_themes[0] if fact_matched_themes else ""
                
                embs_to_add.append(fact_dict.pop("embedding"))
                facts_to_add.append(fact_dict)
            self.vector.add_facts(facts_to_add, embs_to_add)
            
        self.vector.add_episode(episode, episode_embedding)
        
    def _detect_and_resolve_conflicts(self, new_fact_text: str, cand_fact: dict, current_time: str) -> str:
        """충돌 여부를 LLM으로 검증하여 'supersede' 또는 'independent' 반환"""
        cand_text = cand_fact["text"]
        cand_time = cand_fact["metadata"].get("created_at", "Unknown")
        
        prompt = f"""
        <기존 사실>
        내용: {cand_text}
        타임스탬프: {cand_time}
        
        <신규 사실>
        내용: {new_fact_text}
        타임스탬프: {current_time}
        """
        
        messages = [
            {"role": "system", "content": self.conflict_prompt},
            {"role": "user", "content": prompt}
        ]
        
        response_str = self.openai.call_AI(user_request="", not_file=messages, model_set=self.config.judge_model)
        
        if response_str.startswith("❌"):
            return "independent"
            
        json_data = extract_json_from_llm_response(response_str)
        if json_data and "verdict" in json_data:
            return json_data["verdict"]
            
        return "independent"
