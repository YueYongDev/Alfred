# -*- coding: utf-8 -*-
"""
python -m rag_engine.vector_engine
→ 把博客 / 笔记 / 图片 caption 文本写入 Chroma 向量库（带进度条）
"""
from pathlib import Path
import chromadb
from tqdm import tqdm

from llama_index.core import Settings, StorageContext, VectorStoreIndex
from llama_index.vector_stores.chroma import ChromaVectorStore

from rag_engine import config, utils
from rag_engine.providers import get_embed_model, get_extractor_llm
from rag_engine.photos_db import mark_photo_as_indexed


def build_vector_index(photos_to_index: list = None):
    # ① 嵌入 & 轻量 LLM
    Settings.embed_model = get_embed_model()
    llm_dummy = get_extractor_llm()

    if photos_to_index:
        docs = utils.load_photo_docs(photos_to_index)
    else:
        # 如果没有指定照片，则加载所有文本和照片
        # 注意：这里的 load_photo_docs 将需要一个从数据库获取所有照片信息的版本
        # 为了保持一致性，我们应该只通过 photos_to_index 参数来处理照片
        docs = (
            utils.load_markdown_docs(config.BLOG_DIR) +
            utils.load_markdown_docs(config.NOTES_DIR)
        )
        
    total = len(docs)
    if total == 0:
        print("⚠️  没找到任何文档，终止构建。")
        return

    # —— 保证目录存在 ——
    Path(config.VECTOR_DB_DIR).mkdir(parents=True, exist_ok=True)

    # —— ① 建 Chroma PersistentClient ——
    client = chromadb.PersistentClient(path=str(config.VECTOR_DB_DIR))

    # —— ② 拿到（或创建）collection ——
    collection = client.get_or_create_collection(name="alfred_vectors")

    # —— ③ 交给 LlamaIndex ——
    vecdb = ChromaVectorStore(chroma_collection=collection)   # ← 只传这一项

    ctx = StorageContext.from_defaults(vector_store=vecdb)
    index = VectorStoreIndex([], storage_context=ctx, llm=llm_dummy)

    with tqdm(total=total, desc="Indexing vectors", unit="doc") as pbar:
        for doc in docs:
            index.insert(doc)          # 单条插入
            # 从文档的元数据中获取原始文件路径并标记为已索引
            original_file_path = doc.metadata.get('file_path')
            if original_file_path:
                mark_photo_as_indexed(original_file_path)
            pbar.update(1)

    ctx.persist(persist_dir=str(config.VECTOR_DB_DIR))
    print(f"✅ Vector index stored → {config.VECTOR_DB_DIR}")


if __name__ == "__main__":
    # 直接运行此脚本时，将只索引Markdown文档
    build_vector_index()
