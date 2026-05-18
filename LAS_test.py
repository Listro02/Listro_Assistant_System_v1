from MODULE.LAS import LAS
from MODULE.log import log_set
import MODULE.LAS as other

test_log = log_set("LAS_test")
test_log.sys_log.info("✨ 테스트 시작")
test = LAS

test.make_memory("Listro","")




#test.record({"아무거나":"응"})
#test.talking_LAS(content="우리는 뭐하고 있는지 알아? 내가 누구인지도 설명해",name="Listro")
#print(test.summary("Listro","뭐하냐","그냥 개발자님의 요청을 기다리고 있었습니다. 뭐 다른 거라도 기대하셨습니까?","Listro와 라스는 할 것이 없어서 시답잖은 대화나 하고 있다."))
#print(test.summary("Listro","자기소개해봐.","안녕하세요, 저는 L.A.S.입니다. Listro의 개인형 인공지능 비서로, 다양한 질문에 답변하고 도움을 드리기 위해 존재합니다. 프로그램 개발, 기술  관련 정보, 그리고 일반적인 질문에 대해서도 언제든지 문의해 주시면 최선을 다해 도와드리겠습니다. 반갑습니다!","Listro는 라스의 개발을 진행하며 테스트 중이다."))
#print(test.judge("야 뭐하냐"),test.judge("오늘 날씨 어때?"),test.judge("라스야 노래좀 틀어봐"))
#print(test.process("기억 메커니즘이 잘 작동하나보네","Listro"))
#print(test.get_history(2))
#print(other.get_last_line_from_jsonl("C:/Users/taewo/Desktop/Programming/Team_Listro/L.A.S/Project/DATABASE/About_LAS/summary_history.jsonl"))
#LAS.talking_LAS(content="안녕")