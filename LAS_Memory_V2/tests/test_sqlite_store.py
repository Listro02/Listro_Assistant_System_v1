import os
import tempfile
from pathlib import Path
from core.database.sqlite_store import RawMessageStore

def test_insert_and_get_turns():
    fd, temp_db = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    store = RawMessageStore(temp_db)
    id1 = store.insert_turn("user", "Listro", "Hello!")
    id2 = store.insert_turn("assistant", "L.A.S.", "Hi there!")
    
    turns = store.get_turns_by_range(id1, id2)
    assert len(turns) == 2
    assert turns[0]["content"] == "Hello!"
    assert turns[1]["content"] == "Hi there!"

    try:
        os.unlink(temp_db)
    except OSError:
        pass

def test_wal_queue():
    fd, temp_db = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    store = RawMessageStore(temp_db)
    
    # 1. 큐 등록
    wal_id = store.enqueue_wal(1, 10)
    assert wal_id > 0
    
    # 2. 큐 꺼내기
    entry = store.dequeue_wal()
    assert entry is not None
    assert entry["status"] == "processing"
    assert entry["start_turn"] == 1
    assert entry["end_turn"] == 10
    
    # 3. 큐 비어있는지 확인
    assert store.dequeue_wal() is None
    
    # 4. 완료 처리
    store.complete_wal(wal_id)
    
    # 확인
    with store._get_connection() as conn:
        cursor = conn.execute("SELECT status FROM consolidation_wal WHERE id = ?", (wal_id,))
        row = cursor.fetchone()
        assert row["status"] == "done"
    
    try:
        os.unlink(temp_db)
    except OSError:
        pass
