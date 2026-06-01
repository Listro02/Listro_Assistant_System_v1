from core.config import XMemoryConfig
from core.database.vector_store import VectorStore
from core.database.sqlite_store import RawMessageStore
from core.embedding import EmbeddingClient
from core.utils.log_utils import log_set

search_log = log_set("MemoryRetriever")

class MemoryRetriever:
    def __init__(self, config: XMemoryConfig, vector_store: VectorStore, 
                 sqlite_store: RawMessageStore, embedding_client: EmbeddingClient):
        self.config = config
        self.vector = vector_store
        self.sqlite = sqlite_store
        self.embedding = embedding_client

    def retrieve(self, query: str, need_rag: bool = True) -> dict:
        """
        Phase 1 & 2: 전역/국소 검색
        Returns: {"facts": [...], "episodes": [...]}
        """
        if not need_rag:
            return {"facts": [], "episodes": []}
            
        search_log.sys_log.info(f"RAG 검색 시작: '{query[:20]}...'")
        
        # 1. 쿼리 임베딩
        query_emb = self.embedding.embed_text(query)
        
        # 2. Phase 1: 테마 필터링
        theme_ids = self.vector.find_themes(query_emb, threshold=self.config.theme_threshold)
        
        # T_10 (사용자 프로필) 테마는 항상 필터에 포함하여 검색
        search_theme_ids = list(set(theme_ids + ["T_10"]))
        search_log.sys_log.info(f"검색된 테마 (상시 로드 포함): {search_theme_ids}")
        
        # 3. Phase 2: 사실 검색
        all_facts = self.vector.search_facts(query_emb, search_theme_ids, top_k=self.config.fact_top_k)
        
        # 사실 분리: T_10은 user_facts로, 나머지는 일반 facts로 분류
        user_facts = [f for f in all_facts if f.get("metadata", {}).get("parent_theme_id") == "T_10"]
        facts = [f for f in all_facts if f.get("metadata", {}).get("parent_theme_id") != "T_10"]
        
        # 4. Phase 2: 연관 에피소드 로드 (모든 사실 기반)
        episode_ids = list(set([f["metadata"].get("source_episode_id") for f in all_facts if f["metadata"].get("source_episode_id")]))
        episodes = self.vector.get_episodes_by_ids(episode_ids)
        
        return {
            "facts": facts,
            "user_facts": user_facts,
            "episodes": episodes
        }

    def deep_search(self, episode_id: str) -> str:
        """
        Phase 4: 에피소드 ID로 원본 대화(L0) 로드
        """
        search_log.sys_log.info(f"Deep Search 요청: {episode_id}")
        episodes = self.vector.get_episodes_by_ids([episode_id])
        if not episodes:
            return "해당 에피소드를 찾을 수 없습니다."
            
        ep = episodes[0]
        start_id = ep["metadata"].get("target_range_start")
        end_id = ep["metadata"].get("target_range_end")
        
        if not start_id or not end_id:
            return "원본 대화 범위를 알 수 없습니다."
            
        turns = self.sqlite.get_turns_by_range(start_id, end_id)
        
        result = f"=== 에피소드 {episode_id} 원본 대화 ===\n"
        for t in turns:
            result += f"[{t['timestamp']}] {t['name']}: {t['content']}\n"
            
        return result
