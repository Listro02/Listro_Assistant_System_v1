# L.A.S. (Listro's AI Secretary)

L.A.S.는 OpenAI API를 활용하여 상황 판단, 기억 관리, 대화 요약 등의 기능을 독립적인 에이전트 형태로 수행하는 AI 비서 프로젝트입니다. 
단순한 챗봇을 넘어, 사용자의 과거 대화를 기억하고 현재 상황을 판단하여 적절한 도구(음악 재생 등)나 응답을 제공하는 구조를 가지고 있습니다.

## 🚀 주요 기능 (Features)
- **상황 판단 (Judge)**: 사용자의 요청을 분석하여 일반 대화인지, 특정 기능(예: 음악 재생) 수행인지 판단하여 동작을 분기합니다.
- **기억 유지 (Memory)**: 사용자와의 대화 중 중요한 사실(Facts)을 JSONL 형태로 기록하고, 향후 대화에서 문맥으로 활용합니다.
- **자동 요약 (Summary)**: 지속적인 대화 컨텍스트 유지를 위해 대화 내용을 요약하여 관리합니다.
- **로깅 시스템 (Logging)**: 파이썬 데코레이터(`@input_record`)와 커스텀 로거를 통해 실행 흐름과 대화 기록을 체계적으로 추적하고 저장합니다.
- **GUI 환경 지원**: Kivy 프레임워크를 기반으로 한 자체 그래픽 사용자 인터페이스(GUI)를 통해 사용자와 상호작용합니다.

## 🛠 기술 스택 (Tech Stack)
- **Language**: Python 3
- **AI/LLM**: OpenAI API (`gpt-4o-mini`, `gpt-4.1-mini`, `gpt-4.1-nano` 등 모델별 목적 분리)
- **GUI**: Kivy
- **Data Storage**: JSONL (대화 기록, 메모리 등 로컬 기반 경량 데이터 저장)

## 📁 프로젝트 구조 (Project Structure)
```
Project/
├── main.py                # 프로그램 실행 진입점
├── MODULE/                # 핵심 로직 모음
│   ├── LAS.py             # AI 비서 코어 시스템 (판단, 기억, 요약 관리)
│   ├── OPENAI_ai.py       # OpenAI API 통신 모듈
│   ├── GUI_LAS.py         # Kivy 기반 GUI 컨트롤러
│   ├── las_gui_.kv        # Kivy 레이아웃 파일
│   └── log_*.py           # 커스텀 로깅 및 JSONL 입출력 핸들러
├── DATABASE/              # (Git Ignore) 유저 대화 내역 및 기억(Memory) 저장소
├── .env                   # (Git Ignore) API 키 및 경로 환경 변수 
└── .gitignore             # Git 관리 제외 항목 정의
```

## ⚙️ 실행 방법 (Getting Started)
1. 의존성 설치: `pip install -r requirements.txt` (필요시 requirements.txt 생성 권장)
2. 환경 변수 설정: `.env` 파일을 생성하고 발급받은 OpenAI API 키와 저장 경로들을 입력합니다.
3. 애플리케이션 실행:
   ```bash
   python main.py
   ```

## 🌱 향후 개발 목표 (TODO)
- 에러 처리(Error Handling) 고도화
- 모듈간 의존성 및 하드코딩 부분 리팩토링
- 추가 기능(플러그인 형태) 연동
