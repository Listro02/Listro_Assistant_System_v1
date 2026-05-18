from MODULE.OPENAI_ai import OpenAIClient
from functools import wraps
from MODULE.log_json import log_jsonl
from MODULE.log import log_set
from string import Template
from datetime import datetime

from dotenv import load_dotenv
import os
load_dotenv()

from MODULE.control_jsonl import *

#판단 -> 기능 사용

#대화기능 : 요약 자료 체크 -> 응답 -> 요약

LAS_log = log_set("LAS")
log = log_jsonl()
Talking_jsonl = os.getenv("LAS_talking_history")

def input_record(func):
    """라스 클래스 메서드의 호출 정보를 로깅하는 데코레이터"""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        #여기1 - func이전에 실행하는 함수들
        dic1 = {"role" : "user", "name" : "None","content" : ""}
        dic1.update(kwargs)
        log.append_to_jsonl(Talking_jsonl, dic1)
        LAS_log.sys_log.info(f"{dic1['role']}인 \'{dic1['name']}\'의 언급을 Talking_jsonl에 L.A.S. 대화 기록 완료")

        result = func(self,*args, **kwargs) # 받은 인수를 그대로 원본 함수에 전달

        #여기2 - func이후에 실행하는 함수들
        return result
    return wrapper

def extract_json_from_llm_response(llm_response: str) -> dict | None:
    """
    LLM의 전체 응답 문자열에서 JSON 부분만 안전하게 추출합니다.

    Args:
        llm_response (str): <thinking> 태그를 포함할 수 있는 AI의 전체 응답 문자열.

    Returns:
        dict | None: 성공적으로 추출 및 변환된 JSON 데이터 (Python 딕셔너리) 또는 실패 시 None.
    """
    try:
        # 1. JSON 시작점 찾기: 첫 번째 '{'를 찾는다.
        start_index = llm_response.find('{')
        
        # 2. JSON 끝점 찾기: 마지막 '}'를 찾는다. (rfind는 오른쪽부터 찾음)
        end_index = llm_response.rfind('}')

        # 3. 시작점과 끝점이 유효한지 확인
        if start_index != -1 and end_index != -1 and end_index > start_index:
            # 4. JSON 문자열만 잘라내기
            json_string = llm_response[start_index : end_index + 1]
            
            # 5. 잘라낸 문자열을 Python 딕셔너리로 변환
            return json.loads(json_string)
        
        # JSON을 찾지 못한 경우
        print("오류: 응답에서 유효한 JSON 범위를 찾을 수 없습니다.")
        return None

    except json.JSONDecodeError:
        # 5단계에서 변환 실패 시 (JSON 형식이 깨졌을 경우)
        print(f"오류: JSON 형식이 잘못되었습니다. (내용: {json_string})")
        return None
    except Exception as e:
        # 기타 예상치 못한 모든 오류 처리
        print(f"알 수 없는 오류 발생: {e}")
        return None
    
class LAS_SYSTEM:
    def __init__(self):
        self.AI = OpenAIClient()
        self.dic_ai = {"role" : "assistant", "name" : "L.A.S.", "content" : None}
        self.place = "Listro의 개발실"
        self.scenario = "당신은 'Listro의 개발실'에서 당신의 ai비서로써의 역할을 수행하는지 테스트하고 있습니다."


        with open(os.getenv("LAS_memory_prompt"), 'r', encoding='utf-8') as f:
          self.memory_prompt = f.read()

        self.memory_example = get_message_dict(os.getenv("LAS_memory_example"))

        with open(os.getenv("LAS_summary_prompt"), 'r', encoding='utf-8') as f:
          self.summary_prompt = f.read()
        
        with open(os.getenv("LAS_role_prompt"), 'r', encoding='utf-8') as f:
          self.role_prompt = f.read()
        
        with open(os.getenv("LAS_judge_prompt"), 'r', encoding='utf-8') as f:
            self.judge_prompt = f.read()
        
        self.reference = ""
        for i in get_last_n_lines(os.getenv("LAS_reference"),20):
            self.reference += f"Listro: {i["user"]}\nL.A.S.: {i['assistant']}\n"


    def record(self,data):
        """log 기록 method"""
        file = os.getenv("LAS_log")
        summary = os.getenv("LAS_summary_history")

        log_data = {"timestamp":f"{datetime.now()}", "level": "Info", "used_method" : ""}
        log_data.update(data)
        log.append_to_jsonl(file, log_data)

        if log_data["used_method"] == "summary":
            log.append_to_jsonl(summary, log_data)

        LAS_log.sys_log.info(f"✅ record 메서드를 통해 LAS.py 기록됨.")
        pass

    @input_record
    def talking_LAS(self,*,name : str = None,content : str = None,support_list:list = [],example:list =[]):
        """
        LAS의 대화 method
        - name : 사용자의 이름
        - content : 사용자의 발언
        - support_list : %NAME으로 지정된 값 받아서 처리하는 함수, 리스트 형태로 받음. (ex) support = [{"SUMMARY":situation}]
        - example : 대화 예시 "user","assistant" 쌍으로, 리스트 형태로 받음.
        """
        
        LAS_log.sys_log.info("talking_LAS 메서드 사용됨.")

        if name != None:
            content = f"{name}: " + content 
            #사용자가 누군지 말하게 한거임. 근데 이건 judge부분으로 빼서 설정하는게 나을지도
            #고민해봐야지

        messages = Template(self.role_prompt)
        memory = {"facts" : get_x_dict(os.getenv("LAS_memory"),"facts")}
        
        substitutions = {
            'REFERENCE': self.reference,
            'MEMORY': memory,
            'SCENARIO': self.scenario,
            'PLACE': self.place
        }
        for i in support_list:
          substitutions.update(i)
        messages = messages.safe_substitute(substitutions)
           
        messages = [{"role": "system", "content": messages}]
        messages += example
        messages += [{"role":"user","content":content}]

        #그냥 테스트용
        #with open(os.getenv("LAS_prompt_test"),'w',encoding='utf-8') as f:
        #   f.write(str(messages))

        self.dic_ai["content"] = self.AI.call_AI(content, "LAS",not_file=messages,model_set="gpt-4.1-mini",goal="talking") #응답 생성
        log.append_to_jsonl(Talking_jsonl, self.dic_ai)
        LAS_log.sys_log.info(f"✅ talking_LAS 메서드를 통해 답변 생성 완료됨.")

        data = {"used_method" : "talking_LAS", "response": self.dic_ai["content"]}
        self.record(data)

        return self.dic_ai["content"].split("</thinking> ")[1]
    
    def judge(self,content : str,situation:str):
        """현재 요청이 어떤 요청인지 파악하는 method"""
        LAS_log.sys_log.info("judge 메서드 사용됨.")

        messages = [{"role": "system", "content": self.judge_prompt},{"role":"system","content":f"상황 요약 : {situation}"}]
        
        content = f"사용자 입력 : {content}"
        result = self.AI.call_AI(content, "LAS",not_file=messages,model_set="gpt-4o-mini",goal = "Judge")
        LAS_log.sys_log.info(f"✅ judge를 통해 판단 완료됨.")

        data = {"used_method" : "judge", "result(judge)": result}
        self.record(data)

        return result
        

    def summary(self, name:str = None,name_talk=None,las_talk=None, situation : str = None,):
        """summary해서 저장하는 method"""
        LAS_log.sys_log.info("summary 메서드 사용됨.")

        messages = Template(self.summary_prompt)
        messages = messages.safe_substitute(NAME = name)
        messages = [{"role": "system", "content": messages}]

        content = f"Input:\n상황: {situation}\n{name}: {name_talk}\nL.A.S.:{las_talk}"
        result = self.AI.call_AI(content, "LAS",not_file=messages,model_set="gpt-4.1-nano", goal="Summary")
        LAS_log.sys_log.info(f"✅ summary 메서드를 통해 요약 완료됨.")#(f"summary 메서드를 통해 요약됨. : {result}") 이미 openai모듈의 로그로 어떤 답변이 있었는지는 기록됨.
        
        data = {"used_method" : "summary", "result(summary)": result}
        self.record(data)
        return result
    
    def get_history(self,num:int=8):
       """직전의 대화를 가져오는 method"""
       file = os.getenv("LAS_talking_history")
       result = get_last_n_lines(file,num)
       result = [ (a["name"],a["content"],a["role"]) for a in result]
       return_result = []
       for a in result:
          in_ = f"{a[0]}: {a[1]}"
          role = a[2]
          return_result += [{"role": role,"content": in_}]

       LAS_log.sys_log.info(f"✅ get_history 메서드를 통해 이전의 {num}개의 대화 기록 불러와짐.")

       return return_result

    def make_memory(self,name:str,request:str): #기억을 만드는 메서드를 분리하자. L.A.S.의 답변은 따로 처리.
        LAS_log.sys_log.info("make_memory 메서드 사용됨.")

        messages = [{"role": "system", "content": self.memory_prompt}]
        messages += self.memory_example
        content = f"<대화 내용>\n{name}: {request}\n</대화 내용>"


        result = self.AI.call_AI(content,not_file=messages,model_set="gpt-4.1-nano", goal="make_memory")
        result = extract_json_from_llm_response(result) #일단 <thinking>처리해서 fact 딕셔너리 꺼냄
        if result["facts"] == []:
          LAS_log.sys_log.info(f"memory 추가된 내용 없음. : {result["facts"]}")
        else:
          path = f"{os.getenv("LAS_memory_file")}/{name}_memory.jsonl"
          log.append_to_jsonl(path,result)
          LAS_log.sys_log.info(f"✅ {name}_memory.jsonl에 memory 추가됨.")
        #print(messages)
        return result

    def process(self,content,talker:str=None): #talker가 L.A.S.와 대화하는 사람 이름
        """LAS응답처리"""
        if talker == "listro02":
           talker = "Listro"
        self.make_memory(talker,content) #gpt-4.1-nano

        situation = get_last_line_from_jsonl(os.getenv("LAS_summary_history"))
        situation = situation["result(summary)"]
        memory_with_talker = {"facts" : get_x_dict(f"{os.getenv("LAS_memory_file")}/{talker}_memory.jsonl","facts")}
        judge = self.judge(content,situation) #gpt-4o-mini
        support = [{"SUMMARY":situation},{"USER_NAME":talker},{"USER_MEMORY":memory_with_talker}]
        
        if judge == "[음악_재생]":
            support += [{"role":"system","content":"사용 가능 기능 : 음악 재생"}]
            result = self.talking_LAS(content=content,name=talker,support_list=support,example=self.get_history())
            self.summary(talker,content,result,situation)
            self.make_memory("LAS",result)
            LAS_log.sys_log.info(f"✅ process 메서드를 통해 [음악_재생] 기능 사용됨.")
            return result
        
        elif judge == "[일반_대화]":
            result = self.talking_LAS(content=content,name=talker,support_list=support,example=self.get_history()) #gpt-4.1-mini
            self.summary(talker,content,result,situation) #gpt-4.1-nano
            self.make_memory("LAS",result)
            LAS_log.sys_log.info(f"✅ process 메서드를 통해 [일반_대화] 기능 사용됨.")
            return result
        elif judge == "[판단_불가]":
            pass
        else:
            pass

LAS = LAS_SYSTEM()