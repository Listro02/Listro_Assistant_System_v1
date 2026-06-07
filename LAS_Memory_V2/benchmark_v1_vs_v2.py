"""
L.A.S. V1 vs V2 Memory System Benchmark
========================================
기존 메모리(V1, JSONL 기반)와 xMemory(V2, 벡터 DB 기반) 시스템의
응답 지연 시간 및 토큰 소모량 비교 분석.

Usage:
    python benchmark_v1_vs_v2.py           # 실제 API 호출로 벤치마크 실행
    python benchmark_v1_vs_v2.py --dry-run # Mock API로 스크립트 동작 확인
"""

import sys
import os
import time
import json
import shutil
import argparse
import tempfile
from pathlib import Path
from datetime import datetime
from copy import deepcopy

# ──────────────────────────────────────────────────────────────
# Path Setup
# ──────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent   # LAS_Memory_V2/
PROJECT_ROOT = SCRIPT_DIR.parent               # Project/

# V2 imports (core.*) 및 V1 imports (MODULE.*) 모두 지원
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(PROJECT_ROOT))

# Windows CP949 콘솔에서 한글/유니코드 출력 보장
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# .env 로드 (API 키 등)
from dotenv import load_dotenv
load_dotenv(SCRIPT_DIR / ".env")


# ──────────────────────────────────────────────────────────────
# API Metrics Collector
# ──────────────────────────────────────────────────────────────
class APIMetricsCollector:
    """OpenAI API 호출을 래핑하여 지연 시간과 토큰 사용량을 수집"""

    def __init__(self):
        self.chat_calls = []
        self.embedding_calls = []
        self._originals = {}

    def patch(self, openai_raw_client):
        """openai.OpenAI() 인스턴스의 create 메서드를 래핑"""
        self._originals["chat"] = openai_raw_client.chat.completions.create
        self._originals["emb"] = openai_raw_client.embeddings.create
        collector = self
        original_chat = self._originals["chat"]
        original_emb = self._originals["emb"]

        def wrapped_chat(*args, **kwargs):
            start = time.perf_counter()
            response = original_chat(*args, **kwargs)
            elapsed = time.perf_counter() - start
            usage = response.usage
            collector.chat_calls.append({
                "latency_s": round(elapsed, 3),
                "prompt_tokens": usage.prompt_tokens if usage else 0,
                "completion_tokens": usage.completion_tokens if usage else 0,
                "total_tokens": usage.total_tokens if usage else 0,
                "model": response.model,
                "finish_reason": response.choices[0].finish_reason if response.choices else "unknown",
            })
            return response

        def wrapped_emb(*args, **kwargs):
            start = time.perf_counter()
            response = original_emb(*args, **kwargs)
            elapsed = time.perf_counter() - start
            usage = response.usage
            collector.embedding_calls.append({
                "latency_s": round(elapsed, 3),
                "prompt_tokens": usage.prompt_tokens if usage else 0,
                "total_tokens": usage.total_tokens if usage else 0,
                "model": response.model,
            })
            return response

        openai_raw_client.chat.completions.create = wrapped_chat
        openai_raw_client.embeddings.create = wrapped_emb

    def unpatch(self, openai_raw_client):
        """래핑을 해제하여 원래 메서드로 복원"""
        if "chat" in self._originals:
            openai_raw_client.chat.completions.create = self._originals["chat"]
        if "emb" in self._originals:
            openai_raw_client.embeddings.create = self._originals["emb"]
        self._originals = {}

    def reset(self):
        self.chat_calls = []
        self.embedding_calls = []

    def get_summary(self) -> dict:
        total_latency = sum(c["latency_s"] for c in self.chat_calls) + \
                        sum(c["latency_s"] for c in self.embedding_calls)
        total_chat_tok = sum(c["total_tokens"] for c in self.chat_calls)
        total_emb_tok = sum(c["total_tokens"] for c in self.embedding_calls)
        return {
            "total_latency_s": round(total_latency, 3),
            "chat_api_calls": len(self.chat_calls),
            "embedding_api_calls": len(self.embedding_calls),
            "total_api_calls": len(self.chat_calls) + len(self.embedding_calls),
            "chat_prompt_tokens": sum(c["prompt_tokens"] for c in self.chat_calls),
            "chat_completion_tokens": sum(c["completion_tokens"] for c in self.chat_calls),
            "total_chat_tokens": total_chat_tok,
            "total_embedding_tokens": total_emb_tok,
            "total_tokens": total_chat_tok + total_emb_tok,
            "phase4_triggered": any(c.get("finish_reason") == "tool_calls" for c in self.chat_calls),
            "calls_detail": {
                "chat": deepcopy(self.chat_calls),
                "embedding": deepcopy(self.embedding_calls),
            },
        }


# ──────────────────────────────────────────────────────────────
# Dry-Run Mock Setup
# ──────────────────────────────────────────────────────────────
def setup_dry_run_mock(openai_raw_client):
    """API 호출 없이 스크립트 동작만 검증하기 위한 Mock 설정"""
    from unittest.mock import MagicMock

    # Mock chat completions
    def mock_chat_create(*args, **kwargs):
        time.sleep(0.05)  # 시뮬레이션 지연
        mock_resp = MagicMock()
        mock_resp.model = kwargs.get("model", "mock-model")
        mock_resp.usage.prompt_tokens = 500
        mock_resp.usage.completion_tokens = 100
        mock_resp.usage.total_tokens = 600
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].finish_reason = "stop"
        mock_resp.choices[0].message.content = "<thinking>test</thinking> [DRY-RUN] Mock 응답입니다."
        mock_resp.choices[0].message.tool_calls = None
        return mock_resp

    # Mock embeddings
    def mock_emb_create(*args, **kwargs):
        time.sleep(0.02)
        mock_resp = MagicMock()
        mock_resp.model = kwargs.get("model", "mock-embedding")
        mock_resp.usage.prompt_tokens = 50
        mock_resp.usage.total_tokens = 50
        mock_resp.data = [MagicMock()]
        mock_resp.data[0].embedding = [0.01] * 1536
        return mock_resp

    openai_raw_client.chat.completions.create = mock_chat_create
    openai_raw_client.embeddings.create = mock_emb_create


# ──────────────────────────────────────────────────────────────
# Test Utterances
# ──────────────────────────────────────────────────────────────
TEST_CASES = [
    {
        "id": "T1_simple_greeting",
        "label": "단순 인사/리액션",
        "utterance": "야 뭐하냐",
        "expected_path": "NO_RAG → Phase 3 직행",
    },
    {
        "id": "T2_rag_required",
        "label": "과거 정보 필요 (RAG)",
        "utterance": "우리가 처음 만났을 때 무슨 대화를 나눴는지 기억나?",
        "expected_path": "RAG → Phase 1→2→3 (또는 Phase 4)",
    },
    {
        "id": "T3_fact_query",
        "label": "구체적 사실 질문",
        "utterance": "내가 누구인지, 뭘 하고 있는지 설명해봐",
        "expected_path": "RAG → Phase 1→2→3 (Phase 4 가능)",
    },
]


# ──────────────────────────────────────────────────────────────
# V1 Temp Environment Setup (데이터 오염 방지)
# ──────────────────────────────────────────────────────────────
def setup_v1_temp_environment() -> Path:
    """
    V1 시스템의 JSONL 파일 오염을 방지하기 위해,
    기존 데이터 파일을 임시 디렉토리에 복사하고 환경 변수를 리다이렉트.
    """
    temp_dir = Path(tempfile.mkdtemp(prefix="las_benchmark_v1_"))
    temp_about = temp_dir / "DATABASE" / "About_LAS"
    temp_memory = temp_about / "Memory"
    temp_prompt = temp_about / "prompt"

    for d in [temp_about, temp_memory, temp_prompt]:
        d.mkdir(parents=True, exist_ok=True)

    real_about = PROJECT_ROOT / "DATABASE" / "About_LAS"

    # 프롬프트 파일 복사 (읽기 전용이지만 경로 통일을 위해 복사)
    for fname in ["role_prompt.txt", "judge_prompt.txt", "summary_prompt.txt",
                   "memory_prompt.txt", "memory_example.jsonl", "basic_prompt_OPENAI_ai.json"]:
        src = real_about / "prompt" / fname
        if src.exists():
            shutil.copy2(src, temp_prompt / fname)

    # 데이터 파일 복사 (V1이 읽고 쓰는 파일들)
    for fname in ["talking_history.jsonl", "summary_history.jsonl",
                   "reference.jsonl", "log.jsonl"]:
        src = real_about / fname
        if src.exists():
            shutil.copy2(src, temp_about / fname)
        else:
            (temp_about / fname).touch()

    # 메모리 파일 복사
    real_memory = real_about / "Memory"
    if real_memory.exists():
        for f in real_memory.glob("*.jsonl"):
            shutil.copy2(f, temp_memory / f.name)
    # Listro_memory.jsonl이 없으면 빈 파일 생성
    if not (temp_memory / "Listro_memory.jsonl").exists():
        (temp_memory / "Listro_memory.jsonl").touch()

    # 로그 디렉토리 생성
    temp_log = temp_dir / "DATABASE" / "LOG"
    for d in ["SYSTEM_LOGS", "USER_LOGS", "DISCORD_LOGS"]:
        (temp_log / d).mkdir(parents=True, exist_ok=True)

    # 환경 변수 리다이렉트 (V1 모듈이 import될 때 이 경로를 사용)
    os.environ["LAS_talking_history"] = str(temp_about / "talking_history.jsonl")
    os.environ["LAS_log"] = str(temp_about / "log.jsonl")
    os.environ["LAS_role_prompt"] = str(temp_prompt / "role_prompt.txt")
    os.environ["LAS_judge_prompt"] = str(temp_prompt / "judge_prompt.txt")
    os.environ["LAS_summary_prompt"] = str(temp_prompt / "summary_prompt.txt")
    os.environ["LAS_summary_history"] = str(temp_about / "summary_history.jsonl")
    os.environ["LAS_reference"] = str(temp_about / "reference.jsonl")
    os.environ["LAS_memory"] = str(temp_memory / "LAS_memory.jsonl")
    os.environ["LAS_memory_prompt"] = str(temp_prompt / "memory_prompt.txt")
    os.environ["LAS_memory_example"] = str(temp_prompt / "memory_example.jsonl")
    os.environ["LAS_memory_file"] = str(temp_memory)
    os.environ["BASIC_prompt"] = str(temp_prompt / "basic_prompt_OPENAI_ai.json")
    os.environ["SYSTEM_LOGS"] = str(temp_log / "SYSTEM_LOGS")
    os.environ["USER_LOGS"] = str(temp_log / "USER_LOGS")
    os.environ["DISCORD_LOGS"] = str(temp_log / "DISCORD_LOGS")

    print(f"  V1 임시 환경 생성됨: {temp_dir}")
    return temp_dir


# ──────────────────────────────────────────────────────────────
# V1 Benchmark Runner
# ──────────────────────────────────────────────────────────────
def run_v1_benchmark(collector: APIMetricsCollector, test_cases: list, dry_run: bool = False) -> list:
    """V1 (기존 JSONL 기반) 시스템 벤치마크 실행"""
    print("\n" + "=" * 60)
    print("  V1 (Legacy JSONL) 벤치마크 시작")
    print("=" * 60)

    # 임시 환경 설정 (데이터 오염 방지) — V1 모듈 import 전에 실행
    temp_dir = setup_v1_temp_environment()

    results = []
    try:
        # V1 모듈 import (환경 변수가 설정된 상태에서 import해야 함)
        from MODULE.LAS import LAS_SYSTEM
        v1_system = LAS_SYSTEM()

        # Dry-run 모드일 경우 Mock 적용
        if dry_run:
            setup_dry_run_mock(v1_system.AI.client)

        # API 계측 래퍼 적용
        collector.patch(v1_system.AI.client)

        for tc in test_cases:
            print(f"\n  [V1] 테스트: {tc['label']}")
            print(f"       발화: \"{tc['utterance']}\"")

            collector.reset()
            start = time.perf_counter()

            try:
                response = v1_system.process(tc["utterance"], talker="Listro")
            except Exception as e:
                response = f"[ERROR] {e}"
                print(f"       ⚠️ 오류 발생: {e}")

            wall_clock = time.perf_counter() - start
            summary = collector.get_summary()
            summary["wall_clock_s"] = round(wall_clock, 3)
            summary["response_preview"] = (response[:100] + "...") if response and len(response) > 100 else (response or "N/A")
            summary["test_id"] = tc["id"]
            summary["test_label"] = tc["label"]
            summary["utterance"] = tc["utterance"]
            results.append(summary)

            print(f"       응답 시간: {wall_clock:.2f}s | API 호출: {summary['total_api_calls']}회 | 토큰: {summary['total_tokens']:,}")

        collector.unpatch(v1_system.AI.client)

    except Exception as e:
        print(f"\n  ❌ V1 시스템 초기화 실패: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 임시 디렉토리 정리
        try:
            shutil.rmtree(temp_dir)
            print(f"\n  V1 임시 환경 정리됨.")
        except Exception:
            pass

    return results


# ──────────────────────────────────────────────────────────────
# V2 Benchmark Runner
# ──────────────────────────────────────────────────────────────
def run_v2_benchmark(collector: APIMetricsCollector, test_cases: list, dry_run: bool = False) -> list:
    """V2 (xMemory 벡터 DB 기반) 시스템 벤치마크 실행"""
    print("\n" + "=" * 60)
    print("  V2 (xMemory) 벤치마크 시작")
    print("=" * 60)

    results = []
    try:
        from core.manager import XMemoryLAS
        v2_system = XMemoryLAS()

        # Dry-run 모드일 경우 Mock 적용
        if dry_run:
            setup_dry_run_mock(v2_system.AI.client)

        # API 계측 래퍼 적용
        collector.patch(v2_system.AI.client)

        for tc in test_cases:
            print(f"\n  [V2] 테스트: {tc['label']}")
            print(f"       발화: \"{tc['utterance']}\"")

            collector.reset()
            start = time.perf_counter()

            try:
                response = v2_system.process(tc["utterance"], talker="Listro")
            except Exception as e:
                response = f"[ERROR] {e}"
                print(f"       ⚠️ 오류 발생: {e}")

            wall_clock = time.perf_counter() - start
            summary = collector.get_summary()
            summary["wall_clock_s"] = round(wall_clock, 3)
            summary["response_preview"] = (response[:100] + "...") if response and len(response) > 100 else (response or "N/A")
            summary["test_id"] = tc["id"]
            summary["test_label"] = tc["label"]
            summary["utterance"] = tc["utterance"]
            results.append(summary)

            print(f"       응답 시간: {wall_clock:.2f}s | API 호출: {summary['total_api_calls']}회 | 토큰: {summary['total_tokens']:,}")

        collector.unpatch(v2_system.AI.client)

    except Exception as e:
        print(f"\n  ❌ V2 시스템 초기화 실패: {e}")
        import traceback
        traceback.print_exc()

    return results


# ──────────────────────────────────────────────────────────────
# Results Formatter
# ──────────────────────────────────────────────────────────────
def calc_change(v1_val, v2_val) -> str:
    """변화율을 계산하여 문자열로 반환"""
    if v1_val == 0:
        return "N/A"
    pct = ((v2_val - v1_val) / v1_val) * 100
    sign = "+" if pct > 0 else ""
    return f"{sign}{pct:.1f}%"


def print_comparison_table(v1_results: list, v2_results: list):
    """V1과 V2 결과를 비교하여 콘솔에 테이블 출력"""
    print("\n")
    print("=" * 72)
    print("    L.A.S. Memory System Benchmark: V1 vs V2")
    print(f"    실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 72)

    for i, tc in enumerate(TEST_CASES):
        v1 = v1_results[i] if i < len(v1_results) else None
        v2 = v2_results[i] if i < len(v2_results) else None

        print(f"\n  [{tc['id']}] {tc['label']}")
        print(f"  발화: \"{tc['utterance']}\"")
        print("  " + "-" * 66)
        print(f"  {'메트릭':<20} {'V1 (Legacy)':<18} {'V2 (xMemory)':<18} {'변화율':<12}")
        print("  " + "-" * 66)

        if v1 and v2:
            # 응답 시간 (Wall Clock)
            print(f"  {'응답 시간':<20} {v1['wall_clock_s']:.2f}s{'':<13} {v2['wall_clock_s']:.2f}s{'':<13} {calc_change(v1['wall_clock_s'], v2['wall_clock_s'])}")
            # API 지연 합산
            print(f"  {'API 지연 합산':<20} {v1['total_latency_s']:.2f}s{'':<13} {v2['total_latency_s']:.2f}s{'':<13} {calc_change(v1['total_latency_s'], v2['total_latency_s'])}")
            # API 호출 횟수
            print(f"  {'Chat API 호출':<20} {v1['chat_api_calls']}회{'':<15} {v2['chat_api_calls']}회{'':<15} {calc_change(v1['chat_api_calls'], v2['chat_api_calls'])}")
            print(f"  {'Embedding API 호출':<20} {v1['embedding_api_calls']}회{'':<15} {v2['embedding_api_calls']}회{'':<15} {calc_change(v1['embedding_api_calls'], v2['embedding_api_calls'])}")
            print(f"  {'총 API 호출':<20} {v1['total_api_calls']}회{'':<15} {v2['total_api_calls']}회{'':<15} {calc_change(v1['total_api_calls'], v2['total_api_calls'])}")
            # 토큰 소모
            print(f"  {'Chat 토큰':<20} {v1['total_chat_tokens']:,} tok{'':<10} {v2['total_chat_tokens']:,} tok{'':<10} {calc_change(v1['total_chat_tokens'], v2['total_chat_tokens'])}")
            print(f"  {'Embedding 토큰':<20} {v1['total_embedding_tokens']:,} tok{'':<10} {v2['total_embedding_tokens']:,} tok{'':<10} {calc_change(v1['total_embedding_tokens'], v2['total_embedding_tokens'])}")
            print(f"  {'총 토큰 소모':<20} {v1['total_tokens']:,} tok{'':<10} {v2['total_tokens']:,} tok{'':<10} {calc_change(v1['total_tokens'], v2['total_tokens'])}")
            # Phase 4
            v1_p4 = "N/A"
            v2_p4 = "Yes ✓" if v2['phase4_triggered'] else "No"
            print(f"  {'Phase 4 (Deep Search)':<20} {v1_p4:<18} {v2_p4:<18}")
        elif v1:
            print(f"  V2 결과 없음 (초기화 오류)")
        elif v2:
            print(f"  V1 결과 없음 (초기화 오류)")
        else:
            print(f"  양쪽 모두 결과 없음")

        print("  " + "-" * 66)

    # 전체 평균 비교
    if v1_results and v2_results and len(v1_results) == len(v2_results):
        n = len(v1_results)
        v1_avg_time = sum(r["wall_clock_s"] for r in v1_results) / n
        v2_avg_time = sum(r["wall_clock_s"] for r in v2_results) / n
        v1_avg_tok = sum(r["total_tokens"] for r in v1_results) / n
        v2_avg_tok = sum(r["total_tokens"] for r in v2_results) / n
        v1_avg_calls = sum(r["total_api_calls"] for r in v1_results) / n
        v2_avg_calls = sum(r["total_api_calls"] for r in v2_results) / n

        print(f"\n  {'='*66}")
        print(f"  전체 평균 비교 ({n}개 테스트)")
        print(f"  {'-'*66}")
        print(f"  {'평균 응답 시간':<20} {v1_avg_time:.2f}s{'':<13} {v2_avg_time:.2f}s{'':<13} {calc_change(v1_avg_time, v2_avg_time)}")
        print(f"  {'평균 API 호출':<20} {v1_avg_calls:.1f}회{'':<14} {v2_avg_calls:.1f}회{'':<14} {calc_change(v1_avg_calls, v2_avg_calls)}")
        print(f"  {'평균 토큰 소모':<20} {v1_avg_tok:,.0f} tok{'':<10} {v2_avg_tok:,.0f} tok{'':<10} {calc_change(v1_avg_tok, v2_avg_tok)}")
        print(f"  {'='*66}")

    print("\n")


def save_results_json(v1_results: list, v2_results: list, output_path: Path):
    """결과를 JSON 파일로 저장"""
    output = {
        "benchmark_time": datetime.now().isoformat(),
        "test_cases": [tc["id"] for tc in TEST_CASES],
        "v1_results": v1_results,
        "v2_results": v2_results,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"  [SAVE] 결과 JSON 저장: {output_path}")


# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="L.A.S. V1 vs V2 Memory System Benchmark")
    parser.add_argument("--dry-run", action="store_true", help="Mock API로 스크립트 동작만 확인")
    args = parser.parse_args()

    if args.dry_run:
        print("\n  [DRY-RUN] 모드: 실제 API 호출 없이 스크립트 동작만 확인합니다.")

    collector = APIMetricsCollector()

    # ── V1 벤치마크 ──
    v1_results = run_v1_benchmark(collector, TEST_CASES, dry_run=args.dry_run)

    # ── V2 벤치마크 ──
    v2_results = run_v2_benchmark(collector, TEST_CASES, dry_run=args.dry_run)

    # ── 결과 비교 ──
    print_comparison_table(v1_results, v2_results)

    # ── JSON 저장 ──
    json_path = SCRIPT_DIR / "docs" / "benchmark_results.json"
    save_results_json(v1_results, v2_results, json_path)

    print("  [DONE] 벤치마크 완료!")


if __name__ == "__main__":
    main()
