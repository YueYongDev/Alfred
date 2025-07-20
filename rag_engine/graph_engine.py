import inspect

from llama_index.core import KnowledgeGraphIndex, Settings, StorageContext
from llama_index.core.graph_stores import SimpleGraphStore
from tqdm import tqdm

from rag_engine import config, utils
from rag_engine.providers import get_embed_model, get_extractor_llm

# -------- 版本自适应写三元组 --------


def _write_tris(index, tris):
    if hasattr(index, "upsert_triplets"):
        index.upsert_triplets(tris)
        return
    if hasattr(index, "insert_triplets"):
        index.insert_triplets(tris)
        return
    if hasattr(index, "upsert_triplet"):
        sig2 = len(inspect.signature(index.upsert_triplet).parameters) == 2
        for t in tris:
            index.upsert_triplet(t) if sig2 else index.upsert_triplet(*t)
        return
    for t in tris:
        index.insert_triplet(*t)

# -------- 主函数 --------


def build_graph_index(max_triplets_per_chunk=5):
    Settings.embed_model = get_embed_model()
    extractor_llm = get_extractor_llm()

    docs = utils.load_markdown_docs(config.BLOG_DIR) \
        + utils.load_markdown_docs(config.NOTES_DIR) \
        + utils.load_photo_docs(config.PHOTOS_DIR)

    store = SimpleGraphStore()
    ctx = StorageContext.from_defaults(graph_store=store)
    kg = KnowledgeGraphIndex([], storage_context=ctx,
                             max_triplets_per_chunk=max_triplets_per_chunk,
                             llm=extractor_llm)

    for d in tqdm(docs, desc="Building KG"):
        m   = d.metadata
        head = m.get("title", "Untitled")

        tri = [(head, "创建日期", m.get("date", ""))]
        tri += [(head, "标签",  t) for t in m.get("tags", [])]
        tri += [(m["title"], "包含标签", tag) for tag in m.get("ai_tags", [])]
        if "camera" in m:
            tri.append((head, "相机型号", m["camera"]))
        if "lat" in m and "lon" in m:
            tri += [
                (head, "拍摄纬度", str(m["lat"])),
                (head, "拍摄经度", str(m["lon"]))
            ]

        _write_tris(kg, tri)
        kg.insert_nodes([d])

    ctx.persist(persist_dir=config.GRAPH_DB_DIR)
    print(f"✅ KG build done → {config.GRAPH_DB_DIR}")


if __name__ == "__main__":
    build_graph_index()
