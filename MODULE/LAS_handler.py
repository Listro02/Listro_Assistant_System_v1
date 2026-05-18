import os
import openai
import concurrent.futures
from dotenv import load_dotenv

from MODULE.LAS import LAS

# .env 파일에서 환경 변수를 로드합니다.
load_dotenv()

class LAS_Handler:
    """
    별도의 스레드에서 LAS 대화 요청을 안전하게 처리하고,
    결과를 콜백 함수를 통해 비동기적으로 반환하는 클래스입니다.
    """
    def __init__(self, max_workers=5):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("환경 변수에서 'OPENAI_API_KEY'를 찾을 수 없습니다.")
        
        openai.api_key = self.api_key
        
        # 여러 기능(AI, 음악 등)이 공유할 스레드 풀
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        print(f"공유 스레드 풀 (최대 {max_workers}개)을 사용하는 LAS_Handler가 초기화되었습니다.")

    def _blocking_api_call(self, prompt: str,name:str=None) -> str:
        """실제로 LAS를 호출하는 블로킹 함수 (백그라운드 스레드에서 실행됨)"""
        print(f"백그라운드 스레드에서 '{prompt[:20]}...'에 대한 응답 생성 중...")
        try:
            result = LAS.process(content=prompt,talker=name)
            return result
        
        except Exception as e:
            print(f"[오류] LAS 호출 중 예외 발생: {e}")
            return "죄송합니다, 응답을 생성하는 중에 오류가 발생했습니다. 😥"

    def _task_wrapper(self, prompt: str, on_complete_callback,name:str=None):
        """API 호출과 콜백 실행을 감싸는 래퍼 함수"""
        result = self._blocking_api_call(prompt,name=name)
        if on_complete_callback:
            on_complete_callback(result)

    def request_response(self, prompt: str, on_complete,name:str=None):
        """
        외부에서 호출하는 메인 메서드. API 요청 작업을 스레드 풀에 제출합니다.
        """
        if not callable(on_complete):
            raise TypeError("on_complete 인자는 반드시 호출 가능한 함수여야 합니다.")
        
        self.executor.submit(self._task_wrapper, prompt, on_complete,name = name)
        print(f"'{prompt[:20]}...' 요청이 백그라운드 스레드에 전달되었습니다.")

    def shutdown(self):
        """프로그램 종료 시 스레드 풀을 안전하게 종료합니다."""
        print("공유 스레드 풀을 종료합니다...")
        self.executor.shutdown(wait=True)
