import json
from pathlib import Path
from core.database.sqlite_store import RawMessageStore
from core.utils.log_utils import log_set

mig_log = log_set("Migration_L0")

class L0Migrator:
    """기존 talking_history.jsonl을 SQLite Level 0으로 이관"""
    
    def __init__(self, source_path: str | Path, sqlite_store: RawMessageStore):
        self.source_path = Path(source_path)
        self.sqlite_store = sqlite_store
    
    def migrate(self, dry_run: bool = False) -> dict:
        if not self.source_path.exists():
            mig_log.sys_log.error(f"소스 파일을 찾을 수 없습니다: {self.source_path}")
            return {"status": "error", "message": "Source file not found"}
            
        count = 0
        mig_log.sys_log.info(f"L0 마이그레이션 시작: {self.source_path}")
        
        with open(self.source_path, 'r', encoding='utf-8') as f:
            for idx, line in enumerate(f):
                line = line.strip()
                if not line: continue
                try:
                    data = json.loads(line)
                    speaker = data.get("role", "user")
                    name = data.get("name", "Unknown")
                    content = data.get("content", "")
                    
                    # timestamp 로직
                    timestamp = None
                    if "situation" in data and isinstance(data["situation"], dict):
                        timestamp = data["situation"].get("timestamp")
                    
                    if not timestamp:
                        # 1970 + line index
                        hours = idx // 3600
                        minutes = (idx % 3600) // 60
                        seconds = idx % 60
                        timestamp = f"1970-01-01T{hours:02d}:{minutes:02d}:{seconds:02d}"
                        
                    if not dry_run:
                        self.sqlite_store.insert_turn(speaker, name, content, timestamp=timestamp)
                    count += 1
                except Exception as e:
                    mig_log.sys_log.error(f"파싱 오류 (line {idx+1}): {e}")
                    
        mig_log.sys_log.info(f"L0 마이그레이션 완료: {count}건 처리됨 (dry_run={dry_run})")
        return {"status": "success", "count": count}
