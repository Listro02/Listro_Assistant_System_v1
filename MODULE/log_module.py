import logging
from datetime import datetime
from pathlib import Path



"""
# 로그 쓰기
logging.info("시스템 시작")
logging.warning("경고 메시지입니다")
logging.error("에러 발생!")
"""

class log:
    def __init__(self,name:str,path: Path,place:str):
        self.log_dir = path
        self.log_dir.mkdir(exist_ok=True)
        self.log_file = self.log_dir / (datetime.now().strftime('%Y%m%d') + ".log")
        self.place = place

        self.logger = logging.getLogger(name)
        
        # 이미 핸들러가 없을 때에만 추가
        if not self.logger.handlers:
            handler = logging.FileHandler(self.log_file, encoding='utf-8', mode='a')
            fmt = logging.Formatter('[%(asctime)s] [%(place)s] %(levelname)s - %(message)s',
                                    '%Y-%m-%d %H:%M:%S')
            handler.setFormatter(fmt)

            handler.setLevel(logging.DEBUG)  #DEBUG는 모든 메세지 확인 가능
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.DEBUG)
    
    def info(self,msg:str):
        self.logger.info(msg.replace('\n', '\\n'),extra={"place" : self.place}) #test해볼거

    def debug(self,msg:str):
        self.logger.debug(msg.replace('\n', '\\n'),extra={"place" : self.place}) #일단 replace로 \n 문제 방지, 향후에는 filter함수를 추가로 만드는게 베스트

    def warning(self,msg:str):
        self.logger.warning(msg.replace('\n', '\\n'),extra={"place" : self.place})

    def error(self,msg:str):
        self.logger.error(msg.replace('\n', '\\n'),extra={"place" : self.place})

    def critical(self,msg:str):
        self.logger.critical(msg.replace('\n', '\\n'),extra={"place" : self.place})

        
