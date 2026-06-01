import argparse
from pathlib import Path
from core.config import config
from core.database.sqlite_store import RawMessageStore
from core.database.vector_store import VectorStore
from core.embedding import EmbeddingClient
from core.utils.openai_client import OpenAIClient
from core.consolidator.pipeline import ConsolidationPipeline
from core.utils.log_utils import log_set

from migration.migrate_l0 import L0Migrator
from migration.seed_l2_facts import L2Seeder
from migration.bulk_consolidate import BulkConsolidator

run_log = log_set("Migration_Runner")

def main():
    parser = argparse.ArgumentParser(description="L.A.S. xMemory 마이그레이션 스크립트")
    parser.add_argument("--step", type=int, choices=[1, 2, 3], help="실행할 스텝 (1: L0 마이그레이션, 2: L2 시딩, 3: 벌크 통합). 지정하지 않으면 모두 실행.")
    parser.add_argument("--dry-run", action="store_true", help="실제 변경을 가하지 않고 실행")
    parser.add_argument("--max-turns", type=int, default=None, help="Step 3에서 벌크 통합할 최근 N턴의 수 (전체 통합은 생략)")
    args = parser.parse_args()
    
    run_log.sys_log.info("마이그레이션 컴포넌트 초기화 중...")
    sqlite_store = RawMessageStore(config)
    vector_store = VectorStore(config)
    embedding_client = EmbeddingClient(config)
    openai_client = OpenAIClient(config)
    pipeline = ConsolidationPipeline(config, sqlite_store, vector_store, embedding_client, openai_client)
    
    # Project/DATABASE 경로 매핑
    project_root = Path(__file__).resolve().parent.parent.parent
    database_dir = project_root / "DATABASE" / "About_LAS"
    
    source_history = database_dir / "talking_history.jsonl"
    source_las_memory = database_dir / "LAS_memory.jsonl"
    source_listro_memory = database_dir / "Listro_memory.jsonl"
    
    if args.step is None or args.step == 1:
        run_log.sys_log.info("=== Step 1: L0 (Raw Messages) 이관 ===")
        l0_migrator = L0Migrator(source_history, sqlite_store)
        l0_migrator.migrate(dry_run=args.dry_run)
        
    if args.step is None or args.step == 2:
        run_log.sys_log.info("=== Step 2: L2 (과거 요약된 사실) 시딩 ===")
        l2_seeder = L2Seeder([source_las_memory, source_listro_memory], vector_store, embedding_client, config)
        l2_seeder.seed(dry_run=args.dry_run)
        
    if args.step is None or args.step == 3:
        run_log.sys_log.info("=== Step 3: 벌크 LLM 통합 (맥락/L1 생성) ===")
        bulk_runner = BulkConsolidator(pipeline, sqlite_store)
        bulk_runner.run(chunk_size=config.chunk_size, overlap=config.overlap, max_turns=args.max_turns, dry_run=args.dry_run)

    run_log.sys_log.info("=== 마이그레이션 프로세스 완료 ===")

if __name__ == "__main__":
    main()
