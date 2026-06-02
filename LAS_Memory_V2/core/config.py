import os
from dataclasses import dataclass, field
from pathlib import Path

# Project root is 3 levels up from this file (core/config.py -> core -> LAS_Memory_V2 -> Project)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CORE_DIR = Path(__file__).resolve().parent

@dataclass
class XMemoryConfig:
    # 저장소 경로 (core/data/ 기준)
    data_dir: str = str(CORE_DIR / "data")
    prompts_dir: str = str(CORE_DIR / "data" / "prompts")
    store_dir: str = str(CORE_DIR / "data" / "store")
    sqlite_path: str = str(CORE_DIR / "data" / "store" / "raw_messages.db")
    vector_store_dir: str = str(CORE_DIR / "data" / "store" / "vector_store")
    themes_path: str = str(CORE_DIR / "data" / "themes.json")
    
    # 기존 프롬프트 경로 (role_prompt, judge_prompt 등은 기존 위치 참조)
    role_prompt_path: str = os.getenv("LAS_role_prompt", str(CORE_DIR / "data" / "prompts" / "role_prompt.txt"))
    judge_prompt_path: str = os.getenv("LAS_judge_prompt", str(CORE_DIR / "data" / "prompts" / "judge_prompt.txt"))
    reference_path: str = os.getenv("LAS_reference", str(PROJECT_ROOT / "DATABASE" / "About_LAS" / "reference.jsonl"))
    
    # 슬라이딩 윈도우
    window_size: int = 20
    overlap_size: int = 2
    
    # 검색 하이퍼파라미터
    theme_threshold: float = 0.3
    fact_top_k: int = 10
    conflict_threshold: float = 0.85
    
    # 모델
    embedding_model: str = "text-embedding-3-small"
    extraction_model: str = "gpt-4.1-nano"
    main_model: str = "gpt-4.1-mini"
    judge_model: str = "gpt-4o-mini"
    
    # 비동기
    consolidation_workers: int = 2
