import logging
import json
import threading
from datetime import datetime
from pathlib import Path

from core.config import XMemoryConfig

class log:
    def __init__(self, name: str, path: Path, place: str):
        self.log_dir = path
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / (datetime.now().strftime('%Y%m%d') + ".log")
        self.place = place

        self.logger = logging.getLogger(name)
        
        if not self.logger.handlers:
            handler = logging.FileHandler(self.log_file, encoding='utf-8', mode='a')
            fmt = logging.Formatter('[%(asctime)s] [%(place)s] %(levelname)s - %(message)s',
                                    '%Y-%m-%d %H:%M:%S')
            handler.setFormatter(fmt)
            handler.setLevel(logging.DEBUG)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.DEBUG)
    
    def info(self, msg: str):
        self.logger.info(msg.replace('\n', '\\n'), extra={"place": self.place})

    def debug(self, msg: str):
        self.logger.debug(msg.replace('\n', '\\n'), extra={"place": self.place})

    def warning(self, msg: str):
        self.logger.warning(msg.replace('\n', '\\n'), extra={"place": self.place})

    def error(self, msg: str):
        self.logger.error(msg.replace('\n', '\\n'), extra={"place": self.place})

    def critical(self, msg: str):
        self.logger.critical(msg.replace('\n', '\\n'), extra={"place": self.place})


class log_set:
    def __init__(self, place: str):
        config = XMemoryConfig()
        sys_log_path = Path(config.data_dir) / "logs" / "SYSTEM_LOGS"
        self.sys_log = log("SystemLogger", sys_log_path, place)
        self.place = place
        self.sys_log.info(f"xMemory log_set 호출됨.")


class log_jsonl:
    def __init__(self):
        self.jsonl_log = log_set("log_json")
        self.lock = threading.Lock()

    def append_to_jsonl(self, filepath: str | Path, data_dict: dict):
        """주어진 딕셔너리를 .jsonl 파일 끝에 한 줄로 추가합니다. (Thread-safe)"""
        json_string = json.dumps(data_dict, ensure_ascii=False)
        
        with self.lock:
            with open(filepath, 'a', encoding='utf-8') as f:
                f.write(json_string + '\n')
            self.jsonl_log.sys_log.info(f"\'{filepath}\'에 \'{json_string}\'이 추가되었습니다.")
