from MODULE.log_module import log
from pathlib import Path

from dotenv import load_dotenv
import os
load_dotenv()

class log_set:
    def __init__(self,place:str):        
        self.sys_log = log("SystemLogger",Path(os.getenv("SYSTEM_LOGS")),place)
        #self.use_log = log("UserLogger",Path(os.getenv("USER_LOGS")),place)

        self.place = place
        self.sys_log.info(f"log.py 모듈로 호출됨.")
    
    def activate_dicord_log(self):
        self.dis_log = log("DiscordLogger",Path(os.getenv("DISCORD_LOGS")),self.place)
        self.dis_log.debug("🔥 DISCORD 대화 기록 시작됨.")


"""
test = "sys_log와 use_log 객체 작동 테스트"
sys_log.info(test)
use_log.info(test)

sys_log.debug("hi")
"""
