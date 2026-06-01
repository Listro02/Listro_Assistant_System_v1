from pathlib import Path
from core.utils.openai_client import OpenAIClient
from core.utils.json_utils import extract_json_from_llm_response
from core.utils.log_utils import log_set

ext_log = log_set("FactExtractor")

class FactExtractor:
    """Pass 1: 대화 청크에서 Level 2 사실 추출"""
    def __init__(self, openai_client: OpenAIClient, prompt_path: str, model: str = "gpt-4.1-nano"):
        self.client = openai_client
        self.prompt_path = Path(prompt_path)
        self.model = model
        
        with open(self.prompt_path, 'r', encoding='utf-8') as f:
            self.system_prompt = f.read()

    def extract(self, conversation_chunk: list[dict]) -> list[str]:
        """
        대화 청크(리스트 형태의 딕셔너리)를 받아 사실 리스트(문자열)를 반환합니다.
        conversation_chunk: [{"speaker": "user", "name": "Listro", "content": "..."}]
        """
        # Format the chunk into a readable string
        formatted_chunk = []
        for turn in conversation_chunk:
            formatted_chunk.append(f"[{turn['timestamp']}] {turn['name']}: {turn['content']}")
        
        user_request = "<대화 내용>\n" + "\n".join(formatted_chunk) + "\n</대화 내용>"
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_request}
        ]
        
        response_str = self.client.call_AI(user_request="", not_file=messages, model_set=self.model)
        
        # 에러 발생 시 문자열 반환을 방어
        if response_str.startswith("❌"):
            ext_log.sys_log.error(f"Fact 추출 중 오류 발생: {response_str}")
            return []
            
        json_data = extract_json_from_llm_response(response_str)
        if json_data and "facts" in json_data:
            return json_data["facts"]
        
        return []
