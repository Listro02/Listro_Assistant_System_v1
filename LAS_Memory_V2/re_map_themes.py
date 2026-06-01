import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from LAS_Memory_V2.core.manager import XMemoryLAS

def main():
    print("====== xMemory 테마 재매핑(Re-mapping) 시작 ======")
    
    # XMemoryLAS 인스턴스화 시 _init_themes()가 자동 실행되어 
    # level_3_themes 컬렉션에 10개의 테마가 임베딩 및 저장됩니다.
    print("[1] XMemoryLAS 초기화 (테마 임베딩 체크)")
    las = XMemoryLAS()
    vector = las.vector_store
    
    theme_count = vector.themes.count()
    print(f"[*] 현재 DB에 저장된 테마 수: {theme_count}개")
    if theme_count == 0:
        print("[!] 테마가 저장되지 않았습니다. 매니저 초기화 로직을 확인하세요.")
        return

    # 에피소드 데이터 가져오기 (임베딩 포함)
    print("\n[2] 에피소드(Episodes) 데이터 로드 및 재매핑")
    episodes_data = vector.episodes.get(include=["embeddings", "metadatas", "documents"])
    
    ep_ids = episodes_data.get("ids", [])
    ep_embs = episodes_data.get("embeddings", [])
    ep_metas = episodes_data.get("metadatas", [])
    ep_docs = episodes_data.get("documents", [])
    
    episode_to_theme_map = {}
    
    updated_ep_metas = []
    
    for e_id, emb, meta in zip(ep_ids, ep_embs, ep_metas):
        # 새로운 find_themes 로직 적용
        matched_themes = vector.find_themes(emb, threshold=las.config.theme_threshold)
        parent_theme_id = matched_themes[0] if matched_themes else ""
        
        # 메타데이터 업데이트
        meta["parent_theme_id"] = parent_theme_id
        updated_ep_metas.append(meta)
        
        # 매핑 딕셔너리 저장 (나중에 팩트 업데이트에 사용)
        episode_to_theme_map[e_id] = parent_theme_id

    # 에피소드 덮어쓰기 (Upsert)
    if ep_ids:
        vector.episodes.upsert(
            ids=ep_ids,
            embeddings=ep_embs,
            documents=ep_docs,
            metadatas=updated_ep_metas
        )
        print(f"[*] {len(ep_ids)}개의 에피소드 테마 재매핑 및 업데이트 완료.")

    # 팩트 데이터 가져오기
    print("\n[3] 팩트(Facts) 데이터 로드 및 재매핑")
    facts_data = vector.facts.get(include=["embeddings", "metadatas", "documents"])
    
    f_ids = facts_data.get("ids", [])
    f_embs = facts_data.get("embeddings", [])
    f_metas = facts_data.get("metadatas", [])
    f_docs = facts_data.get("documents", [])
    
    updated_f_metas = []
    
    for f_id, meta in zip(f_ids, f_metas):
        source_episode_id = meta.get("source_episode_id", "")
        # 속한 에피소드의 업데이트된 테마 ID 가져오기
        new_theme_id = episode_to_theme_map.get(source_episode_id, "")
        
        meta["parent_theme_id"] = new_theme_id
        updated_f_metas.append(meta)

    # 팩트 덮어쓰기 (Upsert)
    if f_ids:
        vector.facts.upsert(
            ids=f_ids,
            embeddings=f_embs,
            documents=f_docs,
            metadatas=updated_f_metas
        )
        print(f"[*] {len(f_ids)}개의 팩트 테마 재매핑 및 업데이트 완료.")

    print("\n====== 테마 재매핑(Re-mapping) 작업이 완벽히 종료되었습니다! ======")

if __name__ == "__main__":
    main()
