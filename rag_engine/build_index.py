# rag_engine/build_index.py
"""
一键批量构建（或增量更新）：
    python -m rag_engine.build_index
"""

from rag_engine.graph_engine import build_graph_index
from rag_engine.vector_engine import build_vector_index
from rag_engine.photos_db import (
    scan_and_update_photos,
    get_unindexed_photos,
    get_db_connection,
)
from scripts.photo_analyzer import analyze_photo
from tqdm import tqdm


def build_photo_ai_and_index():
    """扫描图片 → AI 分析 → 写 SQLite → 写向量库"""
    print("▶ 扫描并更新照片数据库 …")
    scan_and_update_photos()

    photos = get_unindexed_photos()
    if not photos:
        print("✅ 没有新照片需要分析。")
        return

    print(f"▶️ 发现 {len(photos)} 张新照片，开始视觉分析 …")
    conn, cur = get_db_connection(), None

    with tqdm(total=len(photos), desc="Analyzing photos", unit="photo") as bar:
        cur = conn.cursor()
        for row in photos:
            fp = row["file_path"]
            # {'ai_description': ..., 'ai_tags': ...}
            ai = analyze_photo(fp)

            cur.execute(
                "UPDATE photos SET ai_description = ?, ai_tags = ? WHERE file_path = ?",
                (ai["ai_description"], ai["ai_tags"], fp),
            )
            conn.commit()
            bar.update(1)

    conn.close()
    print("✅ 视觉分析完成，开始写入向量库 …")
    paths = [row["file_path"] for row in get_unindexed_photos()]
    build_vector_index(photos_to_index=paths)
    print("✅ 向量索引完成！")


if __name__ == "__main__":
    # 1. Knowledge-Graph
    build_graph_index()

    # 2. Photo → AI → Vector
    build_photo_ai_and_index()

    print("✨ All done —— KG & Vector up-to-date.")
