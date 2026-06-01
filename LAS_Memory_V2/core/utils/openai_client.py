import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from core.utils.log_utils import log_set
from pathlib import Path

ai_log = log_set("OPENAI_ai_xMemory")

load_dotenv()

class OpenAIClient:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.my_organization = os.getenv("OPENAI_ORGANIZATION")
        self.client = OpenAI(
            api_key=self.api_key,
            organization=self.my_organization
        )

    def call_AI(self, user_request: str, place=None, *, file: Path = None, not_file: list = None, goal: str = None, model_set: str = "gpt-4o"):
        if place != None:
            ai_log.sys_log.info(f"({place}) 🤖 인공지능 대화 기능 호출됨.")
        else:
            ai_log.sys_log.info("🤖 인공지능 대화 기능 호출됨.")
        try:
            if file == None:
                if not_file == None:
                    # 기본 프리셋 프롬프트 - xMemory에서는 가급적 not_file(messages 리스트)를 사용
                    ai_log.sys_log.info("기본 json 프롬프트 입력됨 (not supported in xMemory isolated mode well).")
                    messages = []
                else:
                    messages = not_file
                    ai_log.sys_log.info(f"임의의 json 프롬프트 입력됨. for {goal}")
            else:
                with open(file, 'r', encoding='utf-8') as f:
                    messages = json.load(f)
                    ai_log.sys_log.info(f"임의의 json 프롬프트 입력됨. : {file}")

            messages.append({"role": "user", "content": user_request})

            response = self.client.chat.completions.create(
                model=model_set,
                messages=messages
            )
            result = response.choices[0].message.content
            ai_log.sys_log.info(f"OpenAI API 응답 처리 : {response}")
            ai_log.sys_log.info(f"인공지능 대화 기능의 답변 : {response.choices[0].message.content}")
        except Exception as e:
            result = f"❌ 오류가 발생했습니다. {e}"
            ai_log.sys_log.error(f"❌ 에러 발생 : {e}")
        return result

    def call_AI_with_tools(self, messages: list, tools: list = None, model_set: str = "gpt-4.1-mini") -> dict:
        """도구 호출을 지원하는 확장 API 메서드"""
        ai_log.sys_log.info("🤖 인공지능 Tool Calling 기능 호출됨.")
        kwargs = {
            "model": model_set,
            "messages": messages
        }
        if tools:
            kwargs["tools"] = tools
        
        try:
            response = self.client.chat.completions.create(**kwargs)
            choice = response.choices[0]
            
            # 모델이 도구를 호출했는지 확인
            if choice.finish_reason == "tool_calls":
                ai_log.sys_log.info(f"인공지능 도구 호출 발생: {choice.message.tool_calls}")
                return {
                    "type": "tool_call",
                    "tool_calls": choice.message.tool_calls,
                    "message": choice.message
                }
            else:
                ai_log.sys_log.info(f"인공지능 텍스트 응답: {choice.message.content}")
                return {
                    "type": "text",
                    "content": choice.message.content
                }
        except Exception as e:
            ai_log.sys_log.error(f"❌ call_AI_with_tools 에러 발생 : {e}")
            return {
                "type": "error",
                "content": f"오류 발생: {e}"
            }

    def get_embedding(self, text: str, model: str = "text-embedding-3-small") -> list[float]:
        """텍스트를 벡터로 변환"""
        response = self.client.embeddings.create(
            input=text,
            model=model
        )
        return response.data[0].embedding
