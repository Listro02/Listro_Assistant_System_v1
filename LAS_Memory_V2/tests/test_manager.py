import os
import shutil
from unittest.mock import MagicMock
from core.manager import XMemoryLAS
from core.config import XMemoryConfig
from pathlib import Path

def test_manager_initialization(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy_key")
    # 테스트용 임시 디렉토리 설정
    # Create dummy prompt files and themes
    prompts_dir = tmp_path / "data" / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    with open(prompts_dir / "fact_extract_prompt.txt", "w", encoding="utf-8") as f:
        f.write("dummy prompt")
    with open(prompts_dir / "context_generate_prompt.txt", "w", encoding="utf-8") as f:
        f.write("dummy prompt")
    with open(prompts_dir / "conflict_check_prompt.txt", "w", encoding="utf-8") as f:
        f.write("dummy prompt")
    
    themes_path = tmp_path / "data" / "themes.json"
    with open(themes_path, "w", encoding="utf-8") as f:
        f.write("[]")

    config = XMemoryConfig(
        data_dir=str(tmp_path / "data"),
        prompts_dir=str(prompts_dir),
        store_dir=str(tmp_path / "data" / "store"),
        sqlite_path=str(tmp_path / "data" / "store" / "raw_messages.db"),
        vector_store_dir=str(tmp_path / "data" / "store" / "vector_store"),
        themes_path=str(themes_path)
    )
    
    # Init manager
    manager = XMemoryLAS(config)
    assert manager.place == "Listro의 개발실"
    assert manager.window is not None
    assert manager.sqlite_store is not None
    assert manager.vector_store is not None

def test_manager_judge(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy_key")
    
    # Create dummy files
    prompts_dir = tmp_path / "data" / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    with open(prompts_dir / "fact_extract_prompt.txt", "w", encoding="utf-8") as f:
        f.write("dummy prompt")
    with open(prompts_dir / "context_generate_prompt.txt", "w", encoding="utf-8") as f:
        f.write("dummy prompt")
    with open(prompts_dir / "conflict_check_prompt.txt", "w", encoding="utf-8") as f:
        f.write("dummy prompt")
    
    themes_path = tmp_path / "data" / "themes.json"
    with open(themes_path, "w", encoding="utf-8") as f:
        f.write("[]")

    config = XMemoryConfig(
        data_dir=str(tmp_path / "data"),
        prompts_dir=str(prompts_dir),
        store_dir=str(tmp_path / "data" / "store"),
        sqlite_path=str(tmp_path / "data" / "store" / "raw_messages.db"),
        vector_store_dir=str(tmp_path / "data" / "store" / "vector_store"),
        themes_path=str(themes_path)
    )

    # Mock AI to avoid real API calls
    manager = XMemoryLAS(config)
    manager.AI.call_AI = MagicMock(return_value="[일반_대화][NO_RAG]")
    
    result = manager.judge("안녕!")
    assert result == "[일반_대화][NO_RAG]"
    manager.AI.call_AI.assert_called_once()
