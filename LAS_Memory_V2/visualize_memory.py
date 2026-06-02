import os
import sys
from pathlib import Path

# Add core path to sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from LAS_Memory_V2.core.config import XMemoryConfig
import chromadb
from pyvis.network import Network
import networkx as nx

def main():
    config = XMemoryConfig()
    persist_dir = config.vector_store_dir
    print(f"[*] 벡터 DB 로드 중... ({persist_dir})")
    
    if not os.path.exists(persist_dir):
        print("[!] Vector DB 폴더를 찾을 수 없습니다. 마이그레이션이 완료되었는지 확인하세요.")
        return

    client = chromadb.PersistentClient(path=str(persist_dir))
    
    # 컬렉션 가져오기
    try:
        themes_col = client.get_collection("level_3_themes")
        facts_col = client.get_collection("level_2_facts")
        episodes_col = client.get_collection("level_1_episodes")
    except Exception as e:
        print(f"[!] 컬렉션을 가져오는 중 오류 발생: {e}")
        return

    # 데이터 로드
    themes_data = themes_col.get()
    facts_data = facts_col.get()
    episodes_data = episodes_col.get()
    
    print(f"[*] 테마(Themes): {len(themes_data['ids'])}개")
    print(f"[*] 팩트(Facts): {len(facts_data['ids'])}개")
    print(f"[*] 에피소드(Episodes): {len(episodes_data['ids'])}개")

    # 그래프 생성
    net = Network(height='800px', width='100%', bgcolor='#222222', font_color='white', directed=True)
    # 물리 엔진 설정 (노드들이 예쁘게 퍼지도록)
    net.force_atlas_2based()
    
    # 1. 테마 노드 추가 (최상위)
    # ChromaDB에 테마가 비어있을 수 있으므로 themes.json에서 직접 로드
    themes_path = Path(project_root) / "LAS_Memory_V2" / "core" / "data" / "themes.json"
    import json
    if themes_path.exists():
        with open(themes_path, 'r', encoding='utf-8') as f:
            themes_json_data = json.load(f)
            for theme in themes_json_data:
                t_id = theme.get("id")
                name = theme.get("name", t_id)
                desc = theme.get("summary", "")
                net.add_node(t_id, label=name, title=desc, color='#FF5733', size=40, shape='hexagon')
                
    for t_id, meta in zip(themes_data['ids'], themes_data['metadatas']):
        if t_id not in net.get_nodes():
            name = meta.get("name", t_id)
            desc = meta.get("description", "")
            net.add_node(t_id, label=name, title=desc, color='#FF5733', size=40, shape='hexagon')

    # Add Unclassified node
    net.add_node("T_Unclassified", label="미분류 (Unclassified)", title="테마 매핑 안됨", color='#A0A0A0', size=40, shape='hexagon')

    import textwrap
    
    # 2. 에피소드 노드 추가 (하위/출처)
    for e_id, doc, meta in zip(episodes_data['ids'], episodes_data['documents'], episodes_data['metadatas']):
        summary = doc if doc else "No Summary"
        wrapped_summary = "\n".join(textwrap.wrap(summary, width=60))
        net.add_node(e_id, label=e_id, title=wrapped_summary, color='#33FF57', size=15)

    # 3. 팩트 노드 추가 및 연결
    for f_id, doc, meta in zip(facts_data['ids'], facts_data['documents'], facts_data['metadatas']):
        theme_id = meta.get("parent_theme_id")
        episode_id = meta.get("source_episode_id")
        
        # 팩트 자체를 노드로
        label_text = doc[:15] + "..." if len(doc) > 15 else doc
        wrapped_doc = "\n".join(textwrap.wrap(doc, width=60))
        net.add_node(f_id, label=label_text, title=wrapped_doc, color='#33A1FF', size=25, shape='dot')
        
        # 팩트 -> 테마로 연결 (Belongs To)
        if theme_id and theme_id.strip():
            net.add_edge(f_id, theme_id, title="BELONGS_TO", color='#888888')
        else:
            net.add_edge(f_id, "T_Unclassified", title="BELONGS_TO", color='#A0A0A0')
            
        # 팩트 -> 에피소드로 연결 (Extracted From)
        if episode_id and episode_id.strip():
            # Ensure the episode node exists before adding the edge to avoid Pyvis errors
            if episode_id in episodes_data['ids']:
                net.add_edge(f_id, episode_id, title="EXTRACTED_FROM", color='#555555')

    # 출력 설정
    output_path = os.path.join(os.path.dirname(__file__), "memory_graph.html")
    print(f"[*] 그래프 HTML 생성 중... -> {output_path}")
    
    # 저장
    net.save_graph(output_path)
    print("[*] 성공! 웹 브라우저에서 memory_graph.html 파일을 열어 확인하세요.")

if __name__ == "__main__":
    main()
