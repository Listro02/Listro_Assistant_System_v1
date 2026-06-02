import json

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
