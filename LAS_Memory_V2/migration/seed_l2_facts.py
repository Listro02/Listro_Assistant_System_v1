import json
from pathlib import Path
from datetime import datetime
from core.database.vector_store import VectorStore
from core.embedding import EmbeddingClient
from core.config import XMemoryConfig
from core.utils.log_utils import log_set

mig_log = log_set("Migration_L2_Seeder")

class L2Seeder:
    """기존 memory JSONL의 facts를 ChromaDB Level 2에 시딩"""
    
    def __init__(self, memory_files: list[str], 
                 vector_store: VectorStore,
                 embedding_client: EmbeddingClient,
                 config: XMemoryConfig):
        self.memory_files = [Path(f) for f in memory_files]
        self.vector_store = vector_store
        self.embedding = embedding_client
        self.config = config
    
    def seed(self, dry_run: bool = False) -> dict:
        facts_to_seed = []
        fact_texts = []
        
        mig_log.sys_log.info("L2 시딩 시작")
        
        for file_path in self.memory_files:
            if not file_path.exists():
                mig_log.sys_log.warning(f"시딩 파일 없음: {file_path}")
                continue
                
            filename = file_path.name
            
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line: continue
                    try:
                        data = json.loads(line)
                        if "facts" in data and isinstance(data["facts"], list):
                            for fact_text in data["facts"]:
                                if not fact_text or not isinstance(fact_text, str):
                                    continue
                                    
                                # T_10 강제 매핑
                                if "Listro_memory" in filename:
                                    target_theme = "T_10"
                                    should_seed = True
                                elif "LAS_memory" in filename:
                                    # 정적 페르소나 관련 사실 필터링 (간단한 키워드 필터링)
                                    # 명확하게 role_prompt에 반영된 사실은 제외
                                    skip_keywords = ["주인님", "딱딱한", "수동적인", "신체가 없다", "아부나", "리스트로님"]
                                    if any(k in fact_text for k in skip_keywords):
                                        mig_log.sys_log.info(f"정적 페르소나 시딩 제외: {fact_text}")
                                        should_seed = False
                                    else:
                                        target_theme = None # 나중에 임베딩으로 결정하거나 T_09
                                        should_seed = True
                                else:
                                    target_theme = None
                                    should_seed = True
                                    
                                if should_seed:
                                    # 중복 제거 (대소문자/공백 무시 기준)
                                    normalized_text = fact_text.strip().lower()
                                    if not any(f["text"].strip().lower() == normalized_text for f in facts_to_seed):
                                        facts_to_seed.append({
                                            "text": fact_text,
                                            "parent_theme_id": target_theme
                                        })
                                        fact_texts.append(fact_text)
                    except Exception as e:
                        mig_log.sys_log.error(f"파싱 오류 ({filename}): {e}")
        
        if not facts_to_seed:
            mig_log.sys_log.info("시딩할 사실이 없습니다.")
            return {"status": "success", "count": 0}
            
        mig_log.sys_log.info(f"총 {len(facts_to_seed)}개 사실 추출 완료. 임베딩 생성 중...")
        
        # 임베딩 생성
        embeddings = self.embedding.embed_batch(fact_texts)
        
        # 테마 없는 항목 매핑 및 포맷팅
        formatted_facts = []
        now_str = datetime.now().isoformat()
        
        for idx, (fact, emb) in enumerate(zip(facts_to_seed, embeddings)):
            theme_id = fact["parent_theme_id"]
            if not theme_id:
                # 임베딩으로 테마 검색
                matched = self.vector_store.find_themes(emb, threshold=self.config.theme_threshold)
                if matched:
                    theme_id = matched[0]
                else:
                    theme_id = "T_09" # fallback
            
            f_id = f"F_seed_{int(datetime.now().timestamp())}_{idx}"
            
            formatted_facts.append({
                "id": f_id,
                "text": fact["text"],
                "parent_theme_id": theme_id,
                "status": "active",
                "source_episode_id": "SEED_MIGRATION",
                "created_at": now_str
            })
            
        if not dry_run:
            self.vector_store.add_facts(formatted_facts, embeddings)
            
        mig_log.sys_log.info(f"L2 시딩 완료: {len(formatted_facts)}건 처리됨 (dry_run={dry_run})")
        return {"status": "success", "count": len(formatted_facts)}
