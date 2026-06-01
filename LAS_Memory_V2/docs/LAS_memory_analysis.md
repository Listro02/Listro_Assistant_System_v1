# L.A.S. 기억 시스템 정밀 분석 보고서

> **작성일**: 2026-03-17  
> **분석 관점**: 기술적 전문가 (AI 시스템 설계 / 메모리 아키텍처)

---

## 1. 기억 시스템 전체 구조 개요

L.A.S.의 기억 시스템은 **3개의 독립적인 계층**으로 구성된 계층형 메모리 아키텍처다. 각 계층은 서로 다른 시간 범위를 커버하며, 모두 `LAS_SYSTEM.process()` 호출 하나에서 조합되어 System Prompt에 주입된다.

```
┌─────────────────────────────────────────────────────┐
│                  System Prompt (role_prompt.txt)     │
│  ┌──────────────┐  ┌─────────────────┐  ┌────────┐  │
│  │  $MEMORY     │  │  $USER_MEMORY   │  │$SUMMARY│  │
│  │ (장기/LAS)   │  │  (장기/사용자)  │  │ (중기) │  │
│  └──────┬───────┘  └────────┬────────┘  └───┬────┘  │
└─────────┼────────────────────┼───────────────┼───────┘
          │                    │               │
  LAS_memory.jsonl    {name}_memory.jsonl   summary_history.jsonl
  (영구 사실 목록)     (사용자별 사실 목록)   (마지막 요약 1줄)
  
┌─────────────────────────────────────────────────────┐
│               messages 배열 (단기)                  │
│  get_history(num=8) → talking_history.jsonl 마지막 8턴 │
└─────────────────────────────────────────────────────┘
```

### 계층별 특성 요약

| 계층 | 데이터 소스 | 범위 | 갱신 방식 | 프롬프트 내 위치 |
|---|---|---|---|---|
| **단기 (Short-term)** | [talking_history.jsonl](../../DATABASE/About_LAS/talking_history.jsonl) | 최근 8턴 | 매 발화 자동 추가 | `messages` 배열 (대화 히스토리) |
| **중기 (Mid-term)** | [summary_history.jsonl](../../DATABASE/About_LAS/summary_history.jsonl) | 직전 요약 1줄 | 응답 후 gpt-4.1-nano 요약 | `$SUMMARY` 변수 |
| **장기 (Long-term)** | `{name}_memory.jsonl`, [LAS_memory.jsonl](../../DATABASE/About_LAS/Memory/LAS_memory.jsonl) | 누적 사실 전체 | 응답 전/후 gpt-4.1-nano 추출 | `$USER_MEMORY`, `$MEMORY` 변수 |

---

## 2. 각 계층 정밀 분석

### 2-1. 단기 기억 (Short-term) — [get_history()](../../MODULE/LAS.py#197-211)

**구현 방식:**
```python
# LAS.py - get_history()
def get_history(self, num: int = 8):
    result = get_last_n_lines(file, num)  # deque(maxlen=8)로 마지막 8줄 추출
    return [{"role": role, "content": f"{name}: {content}"} for ...]
```

- `collections.deque(maxlen=N)`을 활용해 **O(N) 전체 파일 스캔** 없이 마지막 N줄 추출
- 추출된 결과는 OpenAI `messages` 배열에 직접 삽입 → 모델이 실제 대화 흐름으로 인식

**실제 데이터 흐름:**
```
talking_history.jsonl (1.3MB, 약 수천 턴 축적)
  → get_last_n_lines(file, 8)
  → [{"role":"user","content":"Listro: 안녕"}, {"role":"assistant","content":"L.A.S.: ..."}]
  → messages 배열에 삽입
```

> [!NOTE]
> [talking_history.jsonl](../../DATABASE/About_LAS/talking_history.jsonl)의 현재 크기가 **1.3MB**에 달함. 파일이 클수록 `deque` 방식은 여전히 전체 파일을 readline()으로 순회하므로 장기적으로 I/O 비용 증가 우려가 있다.

---

### 2-2. 중기 기억 (Mid-term) — [summary()](../../MODULE/LAS.py#181-196)

**구현 방식:**
```python
# LAS.py - summary()
# 1. 이전 요약(situation) + 현재 대화 1쌍을 입력
content = f"Input:\n상황: {situation}\n{name}: {name_talk}\nL.A.S.:{las_talk}"
# 2. gpt-4.1-nano가 "이전 요약을 병합해 새 요약 생성"
result = self.AI.call_AI(content, model_set="gpt-4.1-nano", goal="Summary")
# 3. summary_history.jsonl에 append
```

**프롬프트 설계 분석 ([summary_prompt.txt](../../DATABASE/About_LAS/prompt/summary_prompt.txt)):**
- "과거 대화 내역과 병합" 지침 → **롤링(Rolling) 요약** 방식 채택
- **500자 상한선**: 초과 시 오래된 정보를 점진적으로 삭제하도록 지시
- 다음 호출 시 `$SUMMARY`에 [summary_history.jsonl](../../DATABASE/About_LAS/summary_history.jsonl)의 **마지막 줄 단 1개**만 삽입

> [!IMPORTANT]
> 요약은 **append-only**다. 이전 요약은 읽기 전용이며, 새 요약이 줄로 추가될 뿐 기존 줄이 갱신되지 않는다. 즉, [summary_history.jsonl](../../DATABASE/About_LAS/summary_history.jsonl)은 **요약의 변천 이력**이 축적되는 로그 파일이기도 하다.

---

### 2-3. 장기 기억 (Long-term) — [make_memory()](../../MODULE/LAS.py#212-230)

**구현 방식:**
```python
# LAS.py - make_memory()
# 1. memory_prompt로 gpt-4.1-nano에게 사실 추출 요청
content = f"<대화 내용>\n{name}: {request}\n</대화 내용>"
result = self.AI.call_AI(content, model_set="gpt-4.1-nano", goal="make_memory")
# 2. <thinking> 태그 제거 후 JSON 파싱
result = extract_json_from_llm_response(result)  # {"facts": ["...","..."]}
# 3. 빈 facts가 아닐 때만 append
if result["facts"] != []:
    log.append_to_jsonl(f"{LAS_memory_file}/{name}_memory.jsonl", result)
```

**프롬프트 설계 분석 ([memory_prompt.txt](../../DATABASE/About_LAS/prompt/memory_prompt.txt)):**
- Chain-of-Thought: `<thinking>` 태그 내에서 "정말 영구적 정보인가?"를 자기 검토 후 JSON 출력
- **DON'Ts 분류**: 단순 인사, 일시적 감정, 모호한 발언 명시적 제외

**실제 데이터 예시:**
```json
// LAS_memory.jsonl (L.A.S. 자신에 대한 기억)
{"facts": ["LAS는 딱딱한 말투를 기본으로 하며 유머도 사용할 수 있다."]}
{"facts": ["LAS는 수동적인 성향을 가지고 있다.", "LAS는 주인님의 페이스를 놓치는 것에 대해 걱합니다."]}

// Listro_memory.jsonl (사용자에 대한 기억)
{"facts": ["리스트로는 라스를 개발하는 취미를 가지고 있다."]}
{"facts": ["Listro는 아직 정보 검색 기능을 구현하지 않았다."]}
```

---

## 3. [process()](../../MODULE/LAS.py#231-261) 내 기억 호출 순서 분석

```python
def process(self, content, talker):
    # ① 사용자 발화 → 장기 기억 추출 (make_memory, nano)
    self.make_memory(talker, content)
    
    # ② 중기 기억(요약) 로드
    situation = get_last_line_from_jsonl(LAS_summary_history)["result(summary)"]
    
    # ③ 사용자별 장기 기억 로드
    memory_with_talker = get_x_dict(f"{LAS_memory_file}/{talker}_memory.jsonl", "facts")
    
    # ④ 의도 판단 (judge, gpt-4o-mini)
    judge = self.judge(content, situation)
    
    # ⑤ 통합 System Prompt 구성 후 응답 (talking_LAS, gpt-4.1-mini)
    # → $SUMMARY, $USER_MEMORY, $MEMORY, $REFERENCE 모두 주입
    result = self.talking_LAS(..., support_list=[situation, talker, memory_with_talker])
    
    # ⑥ 응답 → 중기 요약 갱신 (summary, nano)
    self.summary(talker, content, result, situation)
    
    # ⑦ L.A.S. 응답 → L.A.S. 자신의 장기 기억 추출 (make_memory, nano)
    self.make_memory("LAS", result)
```

> [!NOTE]
> 단일 [process()](../../MODULE/LAS.py#231-261) 호출당 **OpenAI API가 최소 4회 호출**된다:
> [make_memory(사용자)](../../MODULE/LAS.py#212-230) → [judge](../../MODULE/LAS.py#165-179) → [talking_LAS](../../MODULE/LAS.py#118-164) → [summary](../../MODULE/LAS.py#181-196) → [make_memory(LAS)](../../MODULE/LAS.py#212-230)
> 즉 응답 1개에 최대 **5 API 호출**이 발생한다.

---

## 4. 현재 구현의 장점

### ✅ 4-1. 계층형 메모리로 컨텍스트 윈도우 압축 효율화
LLM의 컨텍스트 윈도우는 유한하다. Raw 대화를 무한정 넣는 대신, **Short(8턴) + Mid(요약) + Long(사실)** 3계층으로 압축하여 최소 토큰으로 최대 맥락을 전달한다.

### ✅ 4-2. 외부 DB 없는 완전 자립형 아키텍처
SQLite, Pinecone, Chroma 등 벡터 DB 없이 JSONL 파일만으로 구동. 의존성 최소화로 로컬 환경에서도 완전 동작.

### ✅ 4-3. 자기 반성(Self-reflection) 메모리
[make_memory("LAS", result)](../../MODULE/LAS.py#212-230) — L.A.S. 자신도 자신의 응답을 분석해 기억을 갱신한다. 이는 AI가 **자기 자신에 대한 일관된 페르소나**를 유지하는 데 기여한다.

### ✅ 4-4. 사용자별 기억 분리 (`{name}_memory.jsonl`)
멀티유저 환경에서 사용자마다 독립적인 기억 파일을 운영. 개인 정보 섞임 방지 및 개인화 응답 가능.

### ✅ 4-5. Chain-of-Thought 기반의 사실 추출 품질 보장
`<thinking>` 태그를 통한 자기 검토 → 일시적·모호한 정보를 걸러내는 품질 필터 역할.

---

## 5. 현재 구현의 단점 및 AI 비서 역할 수행 시 문제점

### ⚠️ 5-1. **[중요] 장기 기억의 비가역적 오염 (Memory Poisoning)**

```python
# 사실 추출은 append-only, 삭제/수정 메커니즘 없음
log.append_to_jsonl(path, result)  # 한 번 기록된 facts는 영원히 남음
```

**문제**: 잘못 추출된 사실이나 상황이 변한 정보(예: "Listro는 정보 검색 기능을 아직 구현하지 않았다")가 파일에 남아 영원히 프롬프트에 주입된다.

**비서 역할 영향**: AI 비서가 이미 완료된 일을 "아직 안 됐다"고 인식하거나, 변경된 선호도를 구식 정보로 응답할 가능성이 있다.

**필요한 해결책**: 기억 수정(update) / 만료(expire) / 중복 제거(dedup) 메커니즘

---

### ⚠️ 5-2. **[중요] 장기 기억의 무한 누적 및 토큰 폭발**

```python
# talking_LAS()에서 LAS 전체 기억을 매번 전체 로드
memory = {"facts": get_x_dict(os.getenv("LAS_memory"), "facts")}  # 전체 읽기!
```

**문제**: [get_x_dict()](../../MODULE/control_jsonl.py#68-83)는 JSONL 파일의 **모든 `facts`를 단일 리스트로 flatten**하여 System Prompt에 주입한다. 대화량이 쌓일수록 `$MEMORY`와 `$USER_MEMORY` 섹션의 토큰 수가 무한 증가한다.

**비서 역할 영향**:
- 프롬프트 길이 초과 → API 오류 발생 가능 (gpt-4.1-mini의 컨텍스트 한계 도달)
- 토큰 비용 선형 증가
- 관련 없는 오래된 사실들이 노이즈로 작용 → 응답 품질 저하

---

### ⚠️ 5-3. **[중요] 중기 요약(Summary)의 단일 지점 의존성**

```python
# process()에서 요약의 마지막 1줄만 사용
situation = get_last_line_from_jsonl(LAS_summary_history)["result(summary)"]
```

**문제**: 요약 생성(gpt-4.1-nano)이 실패하거나 빈 응답을 반환하면, 다음 호출 시 `situation`이 `None`이 되고 이후 `self.judge(content, None)`, `self.summary(talker, content, result, None)`에 `None`이 그대로 전달되어 **연쇄 오류** 발생 가능성이 있다.

- [get_last_line_from_jsonl()](../../MODULE/control_jsonl.py#4-33) 반환값에 `None` 체크가 없다.
- 요약 자체가 500자 제한 내에서 잘못 압축되면 복구 불가.

---

### ⚠️ 5-4. **단기 기억(Talking History)의 비대칭 구조**

```python
# talking_history.jsonl에 role/name/content가 함께 저장
{"role": "user", "name": "Listro", "content": "안녕"}
{"role": "assistant", "name": "L.A.S.", "content": "안녕하세요."}

# get_history()에서 재구성 시 "name: content" 형태로 합침
{"role": "user", "content": "Listro: 안녕"}
```

**문제**: `role=user` 메시지의 `content`에 `"Listro: 안녕"` 처럼 이름 접두사가 붙은 채로 messages 배열에 삽입된다. OpenAI API 관점에서 이는 유효하지만, **멀티턴 대화 파악의 노이즈**가 될 수 있다. 특히 사용자가 여러 명일 경우 role 구분과 name 구분이 혼용된다.

---

### ⚠️ 5-5. **동시성(Race Condition) 위험**

```python
# LAS_handler.py - ThreadPoolExecutor(max_workers=5)
# 동시에 5개의 요청이 make_memory() → append_to_jsonl() 호출 가능
```

**문제**: `log.append_to_jsonl()`에 파일 쓰기 잠금(lock)이 없다. 여러 Discord 사용자가 동시에 메시지를 보내면, 동일 JSONL 파일에 동시 쓰기가 발생해 **데이터 손상** 가능성이 있다.

```python
# log_json.py - append_to_jsonl() 추정 구현 (잠금 없음)
with open(file, 'a', encoding='utf-8') as f:
    f.write(json.dumps(data, ensure_ascii=False) + '\n')
```

---

### ⚠️ 5-6. **[reference.jsonl](../../DATABASE/About_LAS/reference.jsonl) 초기화 고착 문제**

```python
# LAS_SYSTEM.__init__()에서 단 한 번만 로드
self.reference = ""
for i in get_last_n_lines(os.getenv("LAS_reference"), 20):
    self.reference += f"Listro: {i['user']}\nL.A.S.: {i['assistant']}\n"
```

**문제**: `reference`는 클래스 **초기화 시 단 한 번** 로드되어 **인스턴스 변수로 고정**된다. 런타임 중 [reference.jsonl](../../DATABASE/About_LAS/reference.jsonl)이 업데이트되어도 반영되지 않는다. 장기 운용 시 최신 말투 예시가 반영되지 않는다.

---

## 6. 종합 평가 및 개선 제안

### 전문가 평가
현재 L.A.S.의 기억 시스템은 **MVP(Minimum Viable Product) 수준의 3계층 RAG 유사 아키텍처**로, 외부 의존성 없이 핵심 개념을 올바르게 구현한 점은 높이 평가할 만하다. 그러나 프로덕션 비서 시스템으로 확장하기 위해서는 아래 항목들의 보완이 필요하다.

### 우선순위별 개선 제안

| 우선순위 | 문제 | 권장 해결책 |
|---|---|---|
| 🔴 **Critical** | 장기 기억 무한 누적 + 토큰 폭발 | 기억 항목 수 상한 설정 + 중복 제거(dedup) LLM 패스 추가 |
| 🔴 **Critical** | 파일 동시성(Race Condition) | `threading.Lock()` 또는 `asyncio.Lock()`을 `append_to_jsonl`에 추가 |
| 🟠 **High** | 장기 기억 오염 (수정 불가) | `update/expire` 메커니즘 도입 또는 벡터 DB(Chroma 등)로 마이그레이션 |
| 🟠 **High** | 요약 None 연쇄 오류 | [get_last_line_from_jsonl()](../../MODULE/control_jsonl.py#4-33) 반환값 None 체크 + 기본값 fallback 처리 |
| 🟡 **Medium** | reference 고착 | [talking_LAS()](../../MODULE/LAS.py#118-164) 호출 시마다 최신 N줄 동적 로드 |
| 🟡 **Medium** | talking_history I/O 비용 | 파일 크기 기준 자동 아카이브(rotate) 적용 |
| 🟢 **Low** | API 5회/응답 호출 비용 | make_memory를 비동기로 분리(응답 후 백그라운드 실행)해 응답 지연 단축 |
