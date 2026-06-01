from pathlib import Path
from core.utils.openai_client import OpenAIClient
from core.utils.json_utils import extract_json_from_llm_response
from core.utils.log_utils import log_set
import json

ctx_log = log_set("ContextBuilder")

class ContextBuilder:
    """Pass 2: L1 에피소드 맥락 생성"""
    def __init__(self, openai_client: OpenAIClient, prompt_path: str, model: str = "gpt-4.1-nano"):
        self.client = openai_client
        self.prompt_path = Path(prompt_path)
        self.model = model
        
        with open(self.prompt_path, 'r', encoding='utf-8') as f:
            self.system_prompt = f.read()

    def build(self, chunk: list[dict], facts: list[str]) -> dict:
        """
        원시 대화 청크와 추출된 사실들을 바탕으로 에피소드 맥락을 생성합니다.
        """
        formatted_chunk = []
        for turn in chunk:
            formatted_chunk.append(f"[{turn['timestamp']}] {turn['name']}: {turn['content']}")
            
        user_request = "<대화 원문>\n" + "\n".join(formatted_chunk) + "\n</대화 원문>\n\n"
        user_request += "<추출된 사실들>\n"
        for i, fact in enumerate(facts):
            user_request += f"{i+1}. {fact}\n"
        user_request += "</추출된 사실들>"
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_request}
        ]
        
        response_str = self.client.call_AI(user_request="", not_file=messages, model_set=self.model)
        
        if response_str.startswith("❌"):
            ctx_log.sys_log.error(f"Context 생성 중 오류 발생: {response_str}")
            return {
                "summary": "요약 실패",
                "topics": [],
                "tech_stack": [],
                "conclusion": ""
            }
            
        json_data = extract_json_from_llm_response(response_str)
        if json_data:
            return {
                "summary": json_data.get("summary", ""),
                "topics": json_data.get("topics", []),
                "tech_stack": json_data.get("tech_stack", []),
                "conclusion": json_data.get("conclusion", "")
            }
            
        return {
            "summary": "요약 실패 (JSON 파싱 오류)",
            "topics": [],
            "tech_stack": [],
            "conclusion": ""
        }
