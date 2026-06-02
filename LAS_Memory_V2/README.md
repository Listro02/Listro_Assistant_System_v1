# LAS_Memory_V2 (xMemory Project)

🇺🇸 [English README](README_en.md)

---

## 📖 개요 (Overview)

기존 L.A.S.의 메모리 시스템은 JSONL 기반의 3계층(단기, 중기 요약, 장기 사실) 아키텍처로, 외부 DB 없이 가볍게 동작하는 장점이 있었습니다. 하지만 대화가 누적됨에 따라 **기억 로드로 인한 응답 지연**, **장기 기억의 비가역적 오염(Memory Poisoning)**, 그리고 **토큰 폭발** 등의 한계가 확인되었습니다.

이를 해결하고자 기획된 **xMemory 4-Layer Architecture**는 기존의 평면적인 JSONL 구조를 탈피하여, SQLite 기반의 불변 원시 로그와 ChromaDB 기반의 계층형 벡터 검색(RAG)을 결합한 계층형 메모리 시스템입니다.

---

## ✨ 주요 개선 사항 및 구조 (Key Improvements)

새로운 xMemory 아키텍처는 다음과 같은 특징을 가집니다.

1. **4계층 구조 (4-Layer Architecture)**
   - **Level 3 (테마(Theme) 노드):** 하드코딩된 최상위 관심사 카테고리 (전역 검색용)
   - **Level 2 (사실(Fact) 노드):** 독립적이고 모순이 제거된 단문 명제 (메타데이터 및 상태 관리 지원)
   - **Level 1 (에피소드(Episode) 노드):** 단기 기억에서 밀려난 대화 청크의 다차원 맥락 인덱스
   - **Level 0 (원시(Raw) 대화):** 가공되지 않은 순수 대화 로그 (SQLite 저장, O(1) 로드)

2. **단기 기억의 슬라이딩 윈도우 (Sliding Window)**
   - 기존의 파일 I/O 스캔 방식을 버리고 20턴의 인메모리 큐(Deque)를 활용하여 시계열적 문맥을 보존합니다.
   
3. **비동기 통합 파이프라인 (Async Consolidation)**
   - 단기 기억에서 밀려난 대화는 메인 응답 루프를 차단하지 않고, 백그라운드 워커를 통해 사실 추출 및 벡터 임베딩이 진행됩니다.

4. **심층 검색 도구 (Deep Search Tool Calling)**
   - 평소에는 Level 2 사실과 Level 1 목차만 주입하여 토큰을 절약하고, AI가 필요하다고 판단될 때만 `request_deep_search` 도구를 호출하여 Level 0 원시 대화를 불러옵니다.

---

## 📂 문서 가이드 (Docs)

자세한 분석 및 설계 명세는 `docs` 폴더 내의 문서들을 참고해 주세요.

* [**`LAS_memory_analysis.md`**](./docs/LAS_memory_analysis.md)
  * 기존 L.A.S. 기억 시스템의 정밀 분석 및 문제점(한계점) 도출 보고서
* [**`LAS_technology_analysis.md`**](./docs/LAS_technology_analysis.md)
  * L.A.S. 전체 프로젝트의 기술 스택 및 구조 분석 보고서
* [**`LAS_xMemory_Architecture_v2.md`**](./docs/LAS_xMemory_Architecture_v2.md)
  * **[핵심]** 새로운 xMemory 4계층 아키텍처에 대한 상세 설계 명세서 및 파이프라인 흐름도
* [**`LAS_xMemory_TechStack.md`**](./docs/LAS_xMemory_TechStack.md)
  * xMemory 구현을 위해 결정된 기술 스택(ChromaDB, SQLite, OpenAI Embedding 등)과 디렉토리 변경안

---

## 🚀 마무리

- L.A.S. V2 이전에 RAG 기반 계층형 메모리 아키텍처 구현을 독립된 공간에서 시도해본 것입니다.
- 기존의 L.A.S. kivy UI에 xMemory 활성화 버튼을 두어, 테스트해보는 것이 가능은 합니다.
- 다만, 기존의 시스템에 하드코딩된 부분이 있어 프로젝트의 개발자 외에는 테스트해보기 어려운 부분이 많을 것입니다.
