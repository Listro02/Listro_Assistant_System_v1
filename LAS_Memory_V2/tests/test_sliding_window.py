from core.sliding_window import SlidingWindow

def test_sliding_window():
    window = SlidingWindow(max_size=3, overlap=1)
    
    # 1. 큐 추가
    evict1 = window.push({"role": "user", "content": "1"})
    assert evict1 is None
    
    window.push({"role": "assistant", "content": "2"})
    window.push({"role": "user", "content": "3"})
    
    assert len(window.get_messages()) == 3
    
    # 2. 오버플로우
    evict4 = window.push({"role": "assistant", "content": "4"})
    assert evict4 is not None
    assert len(evict4) == 1
    assert evict4[0]["content"] == "1"
    
    # 3. 오버랩
    overlap = window.get_overlap()
    assert len(overlap) == 1
    assert overlap[0]["content"] == "2"
