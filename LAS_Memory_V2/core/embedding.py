from core.utils.openai_client import OpenAIClient
from core.config import XMemoryConfig

class EmbeddingClient:
    def __init__(self, openai_client: OpenAIClient = None, model: str = None):
        """OpenAI 클라이언트 초기화"""
        self.client = openai_client if openai_client else OpenAIClient()
        self.model = model if model else XMemoryConfig().embedding_model
    
    def embed_text(self, text: str) -> list[float]:
        """단일 텍스트 → 벡터"""
        return self.client.get_embedding(text, model=self.model)
    
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """배치 임베딩 (API 1회 호출로 다수 텍스트 처리)"""
        # OpenAI API allows list of strings for input
        response = self.client.client.embeddings.create(
            input=texts,
            model=self.model
        )
        return [data.embedding for data in response.data]
