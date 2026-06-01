# L.A.S. xMemory 구현을 위한 기술 스택 분석

> **작성일**: 2026-06-01  
> **관련 문서**: [xMemory Architecture v2.0](LAS_xMemory_Architecture_v2.md)  
> **기존 기술 분석**: [LAS_technology_analysis.md](LAS_technology_analysis.md)

---

## 결정이 필요한 5가지 기술 영역

```
┌─────────────────────────────────────────────────────────────────────┐
│                     xMemory 기술 스택 결정 사항                       │
│                                                                     │
│  ① 벡터 DB ─────── L1, L2, L3 벡터 저장 및 메타데이터 필터 검색     │
│  ② 임베딩 모델 ──── 텍스트 → 벡터 변환 (검색 & 통합 파이프라인)     │
│  ③ L0 저장소 ────── 원시 대화 불변 렛저 (RDBMS)                    │
│  ④ 비동기 처리 ──── 기억 통합 파이프라인 백그라운드 실행             │
│  ⑤ Tool Calling ── Phase 3→4 전환을 위한 request_deep_search       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## ① 벡터 데이터베이스 — Level 1, 2, 3 저장소

### 후보 비교

| 기준 | **ChromaDB** | **Qdrant** | **FAISS** |
|---|---|---|---|
| **유형** | 임베디드 벡터 DB | 클라이언트-서버 벡터 DB | 벡터 검색 라이브러리 |
| **설치** | `pip install chromadb` | Docker 또는 pip (서버 필요) | `pip install faiss-cpu` |
| **메타데이터 필터링** | ✅ 내장 (`where={}`) | ✅ 고급 (Payload Indexing) | ❌ 없음 (직접 구현 필요) |
| **영속성** | ✅ `PersistentClient(path=)` | ✅ 네이티브 | ❌ 수동 저장/로드 |
| **외부 서버 필요** | ❌ 프로세스 내 임베디드 | ⚠️ 임베디드 모드 가능하나 제한적 | ❌ 라이브러리 |
| **Python 통합** | 네이티브 Python | Python 클라이언트 | C++ 바인딩 |
| **적합 규모** | 소~중 (수만 벡터) | 중~대 (수백만 벡터) | 대규모 연구용 |

### 추천: **ChromaDB (Embedded Persistent Mode)**

**선택 근거:**

1. **메타데이터 필터링 필수**: xMemory는 `parent_theme_id`, `status`, `source_episode_id` 등의 메타데이터로 검색 공간을 좁혀야 합니다. FAISS는 이를 지원하지 않아 탈락.
2. **제로 인프라**: 기존 L.A.S.는 외부 서버 없이 로컬에서 구동됩니다. ChromaDB의 `PersistentClient`는 별도 서버/Docker 없이 프로세스 내에서 동작.
3. **현재 데이터 규모에 적합**: L3 테마 ~10개, L2 사실 수백~수천, L1 에피소드 수백 수준 → ChromaDB로 충분.
4. **기존 아키텍처 호환**: Kivy + Discord.py의 단일 프로세스 구조에서 임베디드 DB가 가장 자연스러움.

**사용 패턴 예시:**

```python
import chromadb

# 초기화 — 한 번만 생성, 이후 영속
client = chromadb.PersistentClient(path="./DATABASE/xMemory/vector_store")

# Level별 컬렉션 분리
l3_themes   = client.get_or_create_collection("level_3_themes")
l2_facts    = client.get_or_create_collection("level_2_facts")
l1_episodes = client.get_or_create_collection("level_1_episodes")

# Phase 2 검색: L2 Top-K + 메타데이터 필터 (L3 테마 제한)
results = l2_facts.query(
    query_embeddings=[query_vector],
    n_results=10,
    where={
        "$and": [
            {"parent_theme_id": {"$in": ["T_02", "T_04"]}},
            {"status": "active"}
        ]
    }
)
```

> [!NOTE]
> 추후 데이터가 수만 건을 넘어서면 Qdrant로 마이그레이션할 수 있습니다. ChromaDB와 Qdrant는 API 구조가 유사하여 전환 비용이 낮습니다.

---

## ② 임베딩 모델 — 텍스트 → 벡터 변환

### 후보 비교

| 기준 | **OpenAI text-embedding-3-small** | **Sentence-Transformers (로컬)** |
|---|---|---|
| **비용** | $0.02 / 1M 토큰 | 무료 (인프라 비용만) |
| **한국어 성능** | 양호 (범용 다국어) | 우수 (전용 모델 사용 시) |
| **차원 수** | 1,536차원 | 모델 의존 (384~1024) |
| **지연 시간** | API 네트워크 왕복 (~200ms) | 로컬 추론 (~50ms, CPU 기준) |
| **GPU 필요** | ❌ | ⚠️ 없어도 동작하나 느림 |
| **구현 복잡도** | 매우 낮음 (API 1줄) | 중간 (모델 다운로드+관리) |
| **기존 인프라 호환** | ✅ OpenAI 클라이언트 이미 존재 | 새 의존성 추가 필요 |

### 추천: **OpenAI `text-embedding-3-small`** (Phase 1 채택)

**선택 근거:**

1. **기존 인프라 재사용**: [OpenAIClient](../../MODULE/OPENAI_ai.py)가 이미 존재. 임베딩 메서드 추가만으로 즉시 사용 가능.
2. **압도적 비용 효율**: $0.02/1M 토큰. 20턴 대화 청크(~2,000토큰) 기준 **50,000회 임베딩에 $1**. 현실적으로 거의 무료.
3. **한국어 범용 성능 충분**: 기술 문서, 일상 대화, 코드 혼합 등 L.A.S.의 다양한 도메인에서 범용 모델이 오히려 안정적.
4. **구현 단순성**: API 호출 1줄로 벡터 획득 → 개발 속도 최대화.

**구현 예시:**

```python
# OPENAI_ai.py에 메서드 추가
def get_embedding(self, text: str, model: str = "text-embedding-3-small") -> list[float]:
    """텍스트를 벡터로 변환"""
    response = self.client.embeddings.create(
        input=text,
        model=model
    )
    return response.data[0].embedding
```

**비용 시뮬레이션:**

| 시나리오 | 토큰 소비 | 비용 |
|---|---|---|
| L3 테마 초기 임베딩 (9개) | ~500 토큰 | $0.00001 (1회성) |
| 20턴 대화 청크 1건 통합 (L1 요약 + L2 사실 ~5건) | ~3,000 토큰 | $0.00006 |
| 하루 50건 대화 청크 통합 | ~150,000 토큰 | $0.003 |
| **월간 총 임베딩 비용 (추정)** | ~4.5M 토큰 | **~$0.09** |

> [!TIP]
> 추후 한국어 특화 도메인(예: 법률, 의학)이 추가되거나, 오프라인 동작이 필요하면 `sentence-transformers`의 `BGE-M3` 또는 `multilingual-e5-small` 모델로 전환을 검토할 수 있습니다.

---

## ③ Level 0 저장소 — 원시 대화 불변 렛저

### 추천: **SQLite** (Python 표준 라이브러리 `sqlite3`)

**선택 근거:**

1. **제로 의존성**: Python 3.12에 내장. `pip install` 불필요.
2. **WAL 모드 지원**: `PRAGMA journal_mode=WAL` 설정으로 읽기/쓰기 동시성 확보 → 비동기 통합 파이프라인과 메인 루프 충돌 방지.
3. **turn_id 범위 검색 O(1)**: `PRIMARY KEY`로 인덱싱된 `turn_id` 범위 쿼리 → Phase 4의 L0 로드에 최적.
4. **기존 JSONL 대체**: `talking_history.jsonl`의 1.3MB 전체 스캔 문제를 근본 해결.

**스키마 및 초기화:**

```python
import sqlite3

def init_raw_message_db(db_path: str):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")  # 읽기/쓰기 동시성
    conn.execute("""
        CREATE TABLE IF NOT EXISTS raw_messages (
            turn_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp  TEXT    NOT NULL,
            speaker    TEXT    NOT NULL,
            name       TEXT    NOT NULL,
            content    TEXT    NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS consolidation_wal (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            start_turn  INTEGER NOT NULL,
            end_turn    INTEGER NOT NULL,
            status      TEXT    DEFAULT 'pending',
            created_at  TEXT    NOT NULL
        )
    """)
    conn.commit()
    return conn
```

> [!IMPORTANT]
> `consolidation_wal` 테이블이 아키텍처의 **WAL(Write-Ahead Log)** 역할을 수행합니다. 비동기 통합 파이프라인이 처리해야 할 구간을 큐잉하고, 처리 완료 시 `status`를 `'done'`으로 전이시킵니다.

---

## ④ 비동기 처리 — 기억 통합 파이프라인

### 추천: **기존 `ThreadPoolExecutor` 확장**

**선택 근거:**

1. **기존 아키텍처 호환**: [LAS_handler.py](../../MODULE/LAS_handler.py)에서 이미 ThreadPoolExecutor(max_workers=5) 사용 중.
2. **Kivy/Discord 메인 루프 비차단**: 전용 워커를 할당하여 LLM 추출 + 임베딩을 백그라운드에서 처리.
3. **asyncio와 혼합 가능**: 기존 `asyncio.run_coroutine_threadsafe()` 패턴으로 Discord 이벤트 루프에 상태 알림 전달 가능.

**설계 패턴:**

```python
from concurrent.futures import ThreadPoolExecutor
import threading

class MemoryConsolidator:
    def __init__(self, las_system, max_workers=2):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.lock = threading.Lock()  # JSONL/DB 동시 쓰기 방지
        self.las = las_system
    
    def trigger_consolidation(self, evicted_turns: list, overlap_turns: list):
        """단기 윈도우에서 밀려난 턴 + 오버랩 턴을 비동기 처리"""
        chunk = evicted_turns + overlap_turns
        # WAL에 먼저 기록 (데이터 유실 방지)
        self._write_to_wal(chunk)
        # 백그라운드 워커로 전달
        self.executor.submit(self._consolidation_pipeline, chunk)
    
    def _consolidation_pipeline(self, chunk: list):
        """Phase 2 → 3 → 3.5 → 4 순차 실행"""
        # Pass 1: Level 2 사실 추출 (LLM)
        facts = self._extract_facts(chunk)
        # Pass 2: Level 1 맥락 생성 (LLM)
        episode = self._generate_context(chunk, facts)
        # Phase 3: 임베딩 + 매핑
        self._embed_and_map(facts, episode)
        # Phase 3.5: 충돌 감지
        self._detect_conflicts(facts)
        # Phase 4: 테마 매핑 + 커밋
        self._commit_to_db(facts, episode)
```

> [!WARNING]
> 기존 `ThreadPoolExecutor`의 `max_workers=5`에서 **통합 파이프라인 전용 워커를 2개 분리**하는 것을 권장합니다. 메인 대화 처리와 기억 통합이 워커를 경쟁하면 응답 지연이 발생할 수 있습니다.

---

## ⑤ Tool Calling — Phase 3→4 전환 메커니즘

### 추천: **OpenAI Chat Completions API `tools` 파라미터**

기존 [OpenAIClient.call_AI()](../../MODULE/OPENAI_ai.py#L22-L67)를 확장하여 tools 파라미터를 지원해야 합니다.

**도구 스키마 정의:**

```python
DEEP_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "request_deep_search",
        "description": "열람 가능한 과거 기록 목차에서 특정 에피소드의 원시 대화를 로드합니다. "
                       "현재 주입된 사실(Level 2)만으로 답변이 불충분하고, "
                       "목차에 나열된 특정 에피소드에 해답이 있다고 판단될 때만 호출하세요.",
        "parameters": {
            "type": "object",
            "properties": {
                "target_episode": {
                    "type": "string",
                    "description": "로드할 에피소드 ID (예: E_42)"
                },
                "reason": {
                    "type": "string",
                    "description": "이 에피소드를 열람해야 하는 이유"
                }
            },
            "required": ["target_episode", "reason"]
        }
    }
}
```

**call_AI 확장:**

```python
# OPENAI_ai.py 확장
def call_AI_with_tools(self, messages: list, tools: list = None, 
                        model_set: str = "gpt-4.1-mini") -> dict:
    """도구 호출을 지원하는 확장 API 메서드"""
    kwargs = {
        "model": model_set,
        "messages": messages
    }
    if tools:
        kwargs["tools"] = tools
    
    response = self.client.chat.completions.create(**kwargs)
    choice = response.choices[0]
    
    # 모델이 도구를 호출했는지 확인
    if choice.finish_reason == "tool_calls":
        return {
            "type": "tool_call",
            "tool_calls": choice.message.tool_calls,
            "message": choice.message
        }
    else:
        return {
            "type": "text",
            "content": choice.message.content
        }
```

**Phase 3→4 전환 흐름:**

```python
# 1차 생성 (Phase 3)
result = ai.call_AI_with_tools(
    messages=prompt_with_memory,
    tools=[DEEP_SEARCH_TOOL]
)

if result["type"] == "text":
    # 결과 A: L2로 해결 → 파이프라인 종료
    return result["content"]

elif result["type"] == "tool_call":
    # 결과 B: Deep Search 필요 → Phase 4 진입
    tool_call = result["tool_calls"][0]
    args = json.loads(tool_call.function.arguments)
    episode_id = args["target_episode"]
    
    # L0에서 원시 대화 로드 (O(1))
    raw_data = load_raw_episode(episode_id)  # SQLite 범위 쿼리
    
    # 2차 생성 (Phase 4) — 도구 결과를 대화에 추가
    messages += [
        result["message"],  # assistant의 tool_call 메시지
        {"role": "tool", "tool_call_id": tool_call.id, 
         "content": raw_data}
    ]
    final = ai.call_AI_with_tools(messages=messages)
    return final["content"]
```

---

## 종합 기술 스택 요약

### 신규 의존성

| 패키지 | 용도 | 설치 | 비고 |
|---|---|---|---|
| `chromadb` | 벡터 DB (L1, L2, L3) | `pip install chromadb` | 핵심 신규 의존성 |
| `sqlite3` | L0 원시 렛저 + WAL | Python 내장 | 추가 설치 불필요 |
| `openai` (기존) | 임베딩 + LLM + Tool Calling | 이미 설치됨 | 메서드 추가만 필요 |

### 기존 유지 의존성

| 패키지 | 용도 | 변경 사항 |
|---|---|---|
| `openai` | LLM 호출 (judge, talking, 추출) | `tools` 파라미터 지원 확장 |
| `concurrent.futures` | 비동기 워커 | 통합 파이프라인 전용 워커 분리 |
| `threading` | Lock 기반 동시성 제어 | `threading.Lock()` 추가 |
| `collections.deque` | 단기 기억 슬라이딩 윈도우 | `maxlen=20`으로 변경 |
| `python-dotenv` | 환경 변수 관리 | 새 DB 경로 추가 |

### 모델 역할 재배치

| 모델 | 기존 역할 | 신규 역할 |
|---|---|---|
| `gpt-4.1-mini` | 메인 대화 응답 | 메인 대화 응답 + **Tool Calling** (Phase 3-4) |
| `gpt-4o-mini` | 의도 판단 (judge) | **Phase 0 Intent Routing** (RAG 필요 여부 확장) |
| `gpt-4.1-nano` | 요약 + 기억 추출 | ~~요약 폐기~~ / 비동기 **Pass 1 사실 추출** + **Pass 2 맥락 생성** |
| `text-embedding-3-small` | (미사용) | **🆕 임베딩** (L1, L2, L3, 질의 벡터화) |

### 디렉토리 구조 변경안

```
DATABASE/
├── About_LAS/
│   ├── Memory/              ← 기존 (JSONL 기반, 마이그레이션 후 아카이브)
│   ├── prompt/               ← 기존 유지 + 신규 프롬프트 추가
│   │   ├── role_prompt.txt
│   │   ├── judge_prompt.txt  ← Phase 0용 확장
│   │   ├── fact_extract_prompt.txt    ← 🆕 Pass 1 사실 추출용
│   │   ├── context_generate_prompt.txt ← 🆕 Pass 2 맥락 생성용
│   │   └── conflict_check_prompt.txt  ← 🆕 Phase 3.5 충돌 감지용
│   └── ...
├── xMemory/                  ← 🆕 신규 메모리 시스템 루트
│   ├── vector_store/         ← ChromaDB PersistentClient 데이터
│   ├── raw_messages.db       ← SQLite (Level 0 렛저 + WAL 테이블)
│   └── themes.json           ← Level 3 하드코딩 테마 정의
└── ...
```

### 비용 총괄 추정 (월간)

| 항목 | 모델/서비스 | 월간 추정 비용 |
|---|---|---|
| 임베딩 (통합 파이프라인) | text-embedding-3-small | ~$0.09 |
| 임베딩 (질의 벡터화) | text-embedding-3-small | ~$0.01 |
| Pass 1 사실 추출 | gpt-4.1-nano | 기존과 유사 |
| Pass 2 맥락 생성 | gpt-4.1-nano | 기존과 유사 |
| Phase 3.5 충돌 감지 | gpt-4.1-nano | 미미 (충돌 후보 발생 시만) |
| Phase 0 judge | gpt-4o-mini | 기존과 동일 |
| Phase 3-4 대화 생성 | gpt-4.1-mini | 기존과 동일 ~ 소폭 증가 |
| **임베딩 순증 비용** | | **~$0.10/월** |

> [!TIP]
> 실질적으로 **새로 추가되는 비용은 임베딩 비용 월 $0.10 미만**입니다. 기존 5회 일률 호출이 2~4회로 줄어드는 효과와 상쇄하면, 전체 API 비용은 오히려 **감소**할 가능성이 높습니다.
