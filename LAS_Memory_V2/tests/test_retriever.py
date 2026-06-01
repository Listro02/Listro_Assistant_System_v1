from unittest.mock import MagicMock
from core.retriever.search import MemoryRetriever
from core.config import XMemoryConfig

def test_retriever_mocked():
    config = XMemoryConfig()
    mock_sqlite = MagicMock()
    mock_vector = MagicMock()
    mock_embedding = MagicMock()
    
    retriever = MemoryRetriever(config, mock_vector, mock_sqlite, mock_embedding)
    
    # 1. retrieve (need_rag = False)
    result = retriever.retrieve("hello", need_rag=False)
    assert result == {"facts": [], "episodes": []}
    
    # 2. deep search
    mock_vector.get_episodes_by_ids.return_value = [{"metadata": {"target_range_start": 1, "target_range_end": 2}}]
    mock_sqlite.get_turns_by_range.return_value = [
        {"timestamp": "2024-01-01", "name": "user", "content": "hello"}
    ]
    
    deep_result = retriever.deep_search("E_1")
    assert "hello" in deep_result
