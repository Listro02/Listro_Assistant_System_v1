import json
import tempfile
from pathlib import Path
import pytest
from unittest.mock import MagicMock

from core.database.sqlite_store import RawMessageStore
from core.database.vector_store import VectorStore
from migration.migrate_l0 import L0Migrator
from migration.seed_l2_facts import L2Seeder

@pytest.fixture
def temp_history():
    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".jsonl", encoding="utf-8") as f:
        f.write(json.dumps({"role": "user", "name": "TestUser", "content": "Hello", "situation": {"timestamp": "2023-01-01T12:00:00"}}) + "\n")
        f.write(json.dumps({"role": "assistant", "name": "LAS", "content": "Hi", "situation": {"timestamp": "2023-01-01T12:00:05"}}) + "\n")
        path = f.name
    yield path
    Path(path).unlink()

@pytest.fixture
def temp_memory():
    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".jsonl", encoding="utf-8") as f:
        f.write(json.dumps({"facts": ["User likes python"]}) + "\n")
        f.write(json.dumps({"facts": ["LAS is helpful"]}) + "\n")
        path = f.name
    yield path
    Path(path).unlink()

def test_l0_migrator(temp_history):
    mock_sqlite = MagicMock()
    migrator = L0Migrator(temp_history, mock_sqlite)
    res = migrator.migrate(dry_run=True)
    assert res["status"] == "success"
    assert res["count"] == 2

def test_l2_seeder(temp_memory):
    mock_vector = MagicMock()
    mock_embed = MagicMock()
    mock_embed.embed_batch.return_value = [[0.1]*1536, [0.2]*1536]
    mock_config = MagicMock()
    
    seeder = L2Seeder([temp_memory], mock_vector, mock_embed, mock_config)
    res = seeder.seed(dry_run=True)
    
    assert res["status"] == "success"
    assert res["count"] == 2
