# build_index.py
# import torch
import os
import time
from concurrent.futures import ThreadPoolExecutor

from llama_index.core import Settings, StorageContext, Document, PropertyGraphIndex
from llama_index.core.node_parser import SimpleNodeParser
from tqdm import tqdm

from db.database import SessionLocal
from db.models import Note, Blog, Photo
from rag_engine import config
from rag_engine.formatters.formatter import format_note, format_blog, format_photo
from rag_engine.graph_rag.simple_graph_store_with_schema import SimpleGraphStoreWithSchema
from rag_engine.providers import get_embed_model, get_extractor_llm


def batch_process_documents(docs, kg_index, parser, batch_size=4):
    """批量处理文档"""
    total_batches = (len(docs) + batch_size - 1) // batch_size
    batch_bar = tqdm(total=total_batches, desc="⚡ 批量处理", unit="batch")

    with ThreadPoolExecutor(max_workers=2) as executor:  # 限制工作线程数
        futures = []
        for i in range(0, len(docs), batch_size):
            batch = docs[i:i + batch_size]
            futures.append(executor.submit(
                process_document_batch, batch, kg_index, parser
            ))

        for future in futures:
            future.result()
            batch_bar.update(1)
            # log_gpu_memory()  # 记录内存使用

    batch_bar.close()


def process_document_batch(batch, kg_index, parser):
    """处理单批文档"""
    nodes = []
    for doc in batch:
        nodes.extend(parser.get_nodes_from_documents([doc]))
    kg_index.insert_nodes(nodes)


def build_graph_index(max_triplets_per_chunk: int = 10):
    start_time = time.time()

    # 确保存储目录存在
    os.makedirs(config.GRAPH_DB_DIR, exist_ok=True)
    print(f"📁 存储目录: {config.GRAPH_DB_DIR}")

    # 设置全局配置
    Settings.embed_model = get_embed_model()
    extractor_llm = get_extractor_llm()
    print(f"🔧 使用提取模型: {config.EXTRACTION_MODEL}")

    # 初始化图谱存储
    graph_store = SimpleGraphStoreWithSchema()
    storage_context = StorageContext.from_defaults(
        graph_store=graph_store
    )

    # 使用大块节点解析器保持实体完整
    parser = SimpleNodeParser.from_defaults(
        chunk_size=4096,
        chunk_overlap=0
    )

    # 创建知识图谱索引
    print("🛠️ 创建知识图谱索引...")
    kg_index = PropertyGraphIndex(
        [],
        storage_context=storage_context,
        llm=extractor_llm
    )

    # 从数据库获取数据
    print("📥 从数据库加载数据...")
    with SessionLocal() as session:
        notes = session.query(Note).all()
        blogs = session.query(Blog).all()
        photos = session.query(Photo).all()

    print(f"📊 数据统计: {len(notes)}篇笔记, {len(blogs)}篇博客, {len(photos)}张照片")

    # 准备所有文档
    all_docs = []
    for note in notes:
        all_docs.append(Document(text=format_note(note)))
    for blog in blogs:
        all_docs.append(Document(text=format_blog(blog)))
    for photo in photos:
        all_docs.append(Document(text=format_photo(photo)))

    print(f"📚 共 {len(all_docs)} 个文档需要处理")

    # 批量处理文档
    batch_process_documents(all_docs, kg_index, parser, batch_size=4)

    # 统一持久化
    print("💾 持久化索引数据...")
    storage_context.persist(persist_dir=config.GRAPH_DB_DIR)

    duration = time.time() - start_time
    print(f"✅ GraphRAG 索引构建完成! 耗时: {duration // 60:.0f}分 {duration % 60:.0f}秒")
    print(f"📦 存储位置: {config.GRAPH_DB_DIR}")
    print(f"📦 索引ID: {kg_index.index_id}")
    return kg_index
