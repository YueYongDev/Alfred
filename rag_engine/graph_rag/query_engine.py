import os
from llama_index.core import Settings, load_index_from_storage, StorageContext, PropertyGraphIndex
from llama_index.core.query_engine import KnowledgeGraphQueryEngine

from rag_engine import config
from rag_engine.graph_rag.simple_graph_store_with_schema import SimpleGraphStoreWithSchema
from rag_engine.providers import get_llm, get_embed_model

# 全局索引缓存
_index_cache = None


def load_graph_index():
    global _index_cache

    if _index_cache:
        return _index_cache

    if not os.path.exists(config.GRAPH_DB_DIR):
        raise FileNotFoundError(f"索引目录不存在: {config.GRAPH_DB_DIR}")

    required_files = ["docstore.json", "graph_store.json", "index_store.json"]
    missing_files = [f for f in required_files if not os.path.exists(os.path.join(config.GRAPH_DB_DIR, f))]
    if missing_files:
        raise FileNotFoundError(f"索引文件缺失: {', '.join(missing_files)}")

    Settings.llm = get_llm()
    Settings.embed_model = get_embed_model()

    print(f"📂 从 {config.GRAPH_DB_DIR} 加载存储上下文...")

    # ✅ 关键修改：用你的 SimpleGraphStoreWithSchema 显式加载 graph_store
    graph_store = SimpleGraphStoreWithSchema.from_persist_path(
        persist_path=os.path.join(config.GRAPH_DB_DIR, "graph_store.json")
    )

    storage_context = StorageContext.from_defaults(
        persist_dir=config.GRAPH_DB_DIR,
        graph_store=graph_store
    )

    try:
        _index_cache = PropertyGraphIndex(
            [],
            storage_context=storage_context,
            llm=Settings.llm
        )
        print(f"✅ 成功加载知识图谱索引，ID: {_index_cache.index_id}")
        return _index_cache
    except Exception as e:
        print(f"❌ 加载索引失败: {str(e)}")
        print("目录内容:", os.listdir(config.GRAPH_DB_DIR))
        raise


def ask_question(question: str) -> str:
    try:
        print(f"❓ 问题: {question}")
        index = load_graph_index()
        query_engine = index.as_query_engine(
            include_text=True,  # 包含原始文本
            retriever_mode="hybrid",  # 混合检索模式
            verbose=True
        )
        print("🔍 正在查询...")
        response = query_engine.query(question)
        return str(response)
    except Exception as e:
        return f"查询失败: {str(e)}"
