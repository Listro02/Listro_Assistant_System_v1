from collections import deque

class SlidingWindow:
    def __init__(self, max_size: int = 20, overlap: int = 2):
        """인메모리 슬라이딩 윈도우 큐"""
        self._queue: deque = deque(maxlen=max_size)
        self._overlap = overlap
    
    def push(self, turn: dict) -> list[dict] | None:
        """
        턴 추가. 큐 오버플로우 시 밀려난 턴들 반환.
        여기서는 턴이 한 개씩 들어오므로, 큐가 꽉 차있을 때 하나가 밀려납니다.
        하지만 L.A.S.의 설계상 evicted_turns를 chunk 단위로 모아서 처리할 수도 있습니다.
        우선은 1개씩 밀려날 때마다 리스트로 반환합니다.
        
        turn 형식: {"role": "user", "name": "Listro", "content": "..."}
                   (또는 timestamp, turn_id 등을 포함할 수 있음)
        """
        evicted = None
        if len(self._queue) == self._queue.maxlen:
            evicted = [self._queue[0]]
            
        self._queue.append(turn)
        return evicted
    
    def get_messages(self) -> list[dict]:
        """현재 윈도우의 모든 턴을 OpenAI messages 형태로 반환"""
        return [{"role": t["role"], "content": f"{t.get('name', t['role'])}: {t['content']}"} for t in self._queue]
    
    def get_overlap(self) -> list[dict]:
        """오버랩 구간 (현재 큐의 앞쪽 overlap 개수의 턴) 반환"""
        overlap_size = min(self._overlap, len(self._queue))
        return list(self._queue)[:overlap_size]
