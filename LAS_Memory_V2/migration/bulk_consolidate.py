import time
from core.database.sqlite_store import RawMessageStore
from core.consolidator.pipeline import ConsolidationPipeline
from core.utils.log_utils import log_set

bulk_log = log_set("Migration_Bulk")

class BulkConsolidator:
    """SQLite L0 데이터를 바탕으로 Bulk로 L1/L2 생성을 수행"""
    def __init__(self, pipeline: ConsolidationPipeline, sqlite: RawMessageStore):
        self.pipeline = pipeline
        self.sqlite = sqlite
        
    def run(self, chunk_size=20, overlap=2, max_turns=None, dry_run=False):
        max_id = self.sqlite.get_max_turn_id()
        if max_id == 0:
            bulk_log.sys_log.warning("L0 데이터가 없습니다.")
            return {"status": "error", "message": "No L0 data"}
            
        start_id = 1
        if max_turns and max_turns < max_id:
            start_id = max_id - max_turns + 1
            
        bulk_log.sys_log.info(f"벌크 통합 시작: {start_id} ~ {max_id} (chunk={chunk_size}, overlap={overlap})")
        
        step = chunk_size - overlap
        if step <= 0:
            step = chunk_size
            
        wal_ids = []
        # 청크 분할 및 WAL 큐 등록
        for s in range(start_id, max_id + 1, step):
            e = min(s + chunk_size - 1, max_id)
            if not dry_run:
                wid = self.sqlite.enqueue_wal(s, e)
                wal_ids.append(wid)
            else:
                bulk_log.sys_log.info(f"[Dry Run] WAL 큐 등록 예정: {s}~{e}")
                
        if dry_run:
            return {"status": "success", "message": "Dry run completed."}
            
        bulk_log.sys_log.info(f"WAL 큐에 {len(wal_ids)}개 작업 등록 완료. 순차 처리 시작.")
        
        # 순차적으로 파이프라인 직접 호출하여 처리 (로깅 및 모니터링을 위해)
        success_count = 0
        for i in range(len(wal_ids)):
            wal_entry = self.sqlite.dequeue_wal()
            if not wal_entry:
                break
                
            wid = wal_entry['id']
            try:
                bulk_log.sys_log.info(f"[{i+1}/{len(wal_ids)}] 청크 처리 중 ({wal_entry['start_turn']}~{wal_entry['end_turn']})...")
                self.pipeline._run_pipeline(wal_entry)
                self.sqlite.complete_wal(wid)
                success_count += 1
                time.sleep(1) # API Rate limit 방지 (간단한 sleep)
            except Exception as e:
                self.sqlite.fail_wal(wid)
                bulk_log.sys_log.error(f"청크 처리 실패 (WAL ID: {wid}): {e}")
                
        bulk_log.sys_log.info(f"벌크 통합 완료: {success_count}/{len(wal_ids)} 성공")
        return {"status": "success", "total_chunks": len(wal_ids), "success": success_count}
