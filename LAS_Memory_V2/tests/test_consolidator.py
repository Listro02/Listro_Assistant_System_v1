from unittest.mock import MagicMock
from core.consolidator.pipeline import ConsolidationPipeline
from core.config import XMemoryConfig

def test_consolidator_mocked():
    # 이 테스트는 외부 의존성이 많으므로 모킹으로 기본 흐름만 검증합니다.
    config = XMemoryConfig()
    mock_sqlite = MagicMock()
    mock_vector = MagicMock()
    mock_embedding = MagicMock()
    mock_openai = MagicMock()
    
    # 1. Pipeline 초기화
    pipeline = ConsolidationPipeline(config, mock_sqlite, mock_vector, mock_embedding, mock_openai)
    
    # 2. Trigger 검증
    mock_sqlite.enqueue_wal.return_value = 1
    pipeline.trigger(1, 10)
    mock_sqlite.enqueue_wal.assert_called_once_with(1, 10)
