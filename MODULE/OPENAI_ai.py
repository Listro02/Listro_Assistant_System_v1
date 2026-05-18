import os
from openai import OpenAI
from dotenv import load_dotenv
from MODULE.log import log_set
import json

from pathlib import Path

ai_log = log_set("OPENAI_ai")

load_dotenv()

class OpenAIClient:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.my_organization = os.getenv("OPENAI_ORGANIZATION")
        self.client = OpenAI(
            api_key=self.api_key,
            organization=self.my_organization
            )

    def call_AI(self,user_request:str,place=None,*,file:Path=None,not_file:list=None,goal:str=None,model_set:str = "gpt-4o"):
        """
        openai response를 가져오는 함수
        - json에 있는거나 not_file이라도 모두 가져와지는건 list여야함.

        - not_file 변수를 쓸 경우 : {"role":"system","content":messages} 이런 양식으로 보내야함.
        - file 변수를 쓸 경우 : json 파일 경로를 받음.
        - file도 not_file 변수도 사용 안했을 경우 : 기본 json 프롬프트가 쓰임.
        """
        if place != None:
            ai_log.sys_log.info(f"({place}) 🤖 인공지능 대화 기능 호출됨.")
        else:
            ai_log.sys_log.info("🤖 인공지능 대화 기능 호출됨.")
        try:
            #k = 1 / 0 #오류 인식 잘됨. good

            if file == None:
                if not_file == None:
                    #기본 프리셋 프롬프트
                    with open(os.getenv("BASIC_prompt"), 'r', encoding='utf-8') as f:
                        messages = json.load(f)
                        ai_log.sys_log.info("기본 json 프롬프트 입력됨.")
                else:
                    #파일이 아니라 아애 딕셔너리들로 이루어진 리스트로 전달 받을 경우
                    messages = not_file
                    ai_log.sys_log.info(f"임의의 json 프롬프트 입력됨. for {goal}")
            else:
                #파일 위치를 받을 경우
                with open(file, 'r', encoding='utf-8') as f:
                    messages = json.load(f)
                    ai_log.sys_log.info(f"임의의 json 프롬프트 입력됨. : {file}")

            messages.append({"role": "user", "content": user_request})

            response = self.client.chat.completions.create(
            model=model_set,
            messages=messages
            )
            #print(messages)
            result = response.choices[0].message.content
            ai_log.sys_log.info(f"OpenAI API 응답 처리 : {response}")
            ai_log.sys_log.info(f"인공지능 대화 기능의 답변 : {response.choices[0].message.content}")
        except Exception as e:
            result = f"❌ 오류가 발생했습니다. {e}"
            ai_log.sys_log.error(f"❌ 에러 발생 : {e}")
        return result
    

