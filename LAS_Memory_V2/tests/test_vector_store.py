import os
import shutil
import tempfile
from core.database.vector_store import VectorStore

def test_themes():
    temp_dir = tempfile.mkdtemp()
    temp_vstore = VectorStore(temp_dir)

    themes = [
        {"id": "T_01", "name": "AI", "description": "AI Test"}
    ]
    embeddings = [[0.1, 0.2, 0.3]]
    temp_vstore.init_themes(themes, embeddings)
    
    # Cosine distance = 1 - similarity. Here query is identical, so dist is 0
    matched = temp_vstore.find_themes([0.1, 0.2, 0.3], threshold=0.9)
    assert matched == ["T_01"]
    shutil.rmtree(temp_dir, ignore_errors=True)

def test_facts():
    temp_dir = tempfile.mkdtemp()
    temp_vstore = VectorStore(temp_dir)
    
    facts = [{
        "id": "F_1",
        "text": "User likes Python",
        "parent_theme_id": "T_01",
        "status": "active"
    }]
    embeddings = [[0.5, 0.5, 0.5]]
    
    temp_vstore.add_facts(facts, embeddings)
    
    results = temp_vstore.search_facts([0.5, 0.5, 0.5], ["T_01"], top_k=1)
    assert len(results) == 1
    assert results[0]["id"] == "F_1"
    
    # test supersede
    temp_vstore.supersede_fact("F_1", "F_2")
    results = temp_vstore.search_facts([0.5, 0.5, 0.5], ["T_01"], top_k=1)
    assert len(results) == 0  # Should be 0 since status is now superseded
    shutil.rmtree(temp_dir, ignore_errors=True)

def test_episodes():
    temp_dir = tempfile.mkdtemp()
    temp_vstore = VectorStore(temp_dir)
    
    episode = {
        "id": "E_1",
        "summary": "Talked about python",
        "parent_theme_id": "T_01",
        "topics": ["python", "coding"]
    }
    embedding = [0.2, 0.2, 0.2]
    
    temp_vstore.add_episode(episode, embedding)
    
    results = temp_vstore.get_episodes_by_ids(["E_1"])
    assert len(results) == 1
    assert results[0]["id"] == "E_1"
    assert "python" in results[0]["topics"]
    shutil.rmtree(temp_dir, ignore_errors=True)
