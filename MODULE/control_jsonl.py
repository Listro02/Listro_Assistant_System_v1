import json
from collections import deque

def get_last_line_from_jsonl(file_path):
  """
  JSONL 파일의 마지막 줄을 읽어 파싱된 JSON 객체를 반환합니다.

  Args:
    file_path: JSONL 파일의 경로

  Returns:
    파싱된 JSON 객체 또는 파일이 비어있을 경우 None
  """
  last_line = None
  try:
    with open(file_path, 'rb') as f:
      # 파일의 끝으로 이동하여 마지막 줄을 효율적으로 찾습니다.
      f.seek(-2, 2)
      while f.read(1) != b'\n':
        f.seek(-2, 1)
      last_line = f.readline().decode()
  except OSError:
    # 파일이 너무 작거나 비어있는 경우 전체를 읽습니다.
    with open(file_path, 'r', encoding='utf-8') as f:
      lines = f.readlines()
      if lines:
        last_line = lines[-1]

  if last_line:
    return json.loads(last_line)
  else:
    return None

def get_last_n_lines(file_path, num_lines):
  """
  JSONL 파일의 마지막 N개의 줄을 파싱하여 딕셔너리 리스트로 반환합니다.

  Args:
    file_path (str): JSONL 파일 경로
    num_lines (int): 가져올 마지막 줄의 개수

  Returns:
    list: 마지막 N개의 JSON 객체가 변환된 딕셔너리 리스트
  """
  try:
    with open(file_path, 'r', encoding='utf-8') as f:
      # 최대 길이를 num_lines로 설정한 deque를 생성합니다.
      last_lines_deque = deque(f, maxlen=num_lines)

    # deque에 남아있는 마지막 N개의 줄을 파싱하여 리스트로 만듭니다.
    return [json.loads(line) for line in last_lines_deque]
  except FileNotFoundError:
    return []
  except json.JSONDecodeError:
    print(f"Error: 파일 '{file_path}'의 내용 중 JSON 형식이 아닌 줄이 있습니다.")
    return []

def read_jsonl_as_string(filepath):
    """
    JSONL 파일 전체를 하나의 문자열로 읽어옵니다.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return f"오류: '{filepath}' 파일을 찾을 수 없습니다."

def get_x_dict(filepath,x:str):
    """
    리스트를 반환합니다.
    - {"x" : []} 형태로 된 파일을 받습니다.
    """
    try:
       with open(filepath, 'r', encoding='utf-8') as f:
        result = []
        for line in f:
            # 각 줄을 JSON 객체로 변환합니다.
            data = json.loads(line)
            result.extend(data[x])
        return result
    except FileNotFoundError:
        return f"오류: '{filepath}' 파일을 찾을 수 없습니다."

def get_message_dict(filepath):
    """
    리스트를 반환합니다.
    - {"messages" : []} 형태로 된 파일을 받습니다.
    """
    try:
       with open(filepath, 'r', encoding='utf-8') as f:
        result = []
        for line in f:
            # 각 줄을 JSON 객체로 변환합니다.
            data = json.loads(line)
            # "messages" 키에 담긴 리스트를 result에 추가합니다.
            # 주의: OpenAI API는 메시지 리스트를 그대로 받지 않고, 개별 딕셔너리를 받으므로 extend를 사용합니다.
            result.extend(data['messages'])
        return result
    except FileNotFoundError:
        return f"오류: '{filepath}' 파일을 찾을 수 없습니다."