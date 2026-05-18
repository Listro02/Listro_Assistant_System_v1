import json
import os
from MODULE.log import log_set
from datetime import datetime
from pathlib import Path

class log_jsonl:
    def __init__(self):
        self.jsonl_log = log_set("log_json")
        #사용 예시 : self.jsnol_log.sys_log.info("✅ 로드되었습니다.")

    def append_to_jsonl(self,filepath: Path, data_dict: dict):
        """주어진 딕셔너리를 .jsonl 파일 끝에 한 줄로 추가합니다."""
        # 딕셔너리를 한 줄의 JSON 문자열로 변환 (ensure_ascii=False는 한글 처리용)
        json_string = json.dumps(data_dict, ensure_ascii=False)
        
        # 파일을 추가 모드('a')로 열고 한 줄 쓰기
        with open(filepath, 'a', encoding='utf-8') as f:
            f.write(json_string + '\n')
            self.jsonl_log.sys_log.info(f"\'{filepath}\'에 \'{json_string}\'이 추가되었습니다.")

    