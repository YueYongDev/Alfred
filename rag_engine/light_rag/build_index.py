import os

from lightrag import LightRAG
from lightrag.kg.shared_storage import initialize_pipeline_status
from lightrag.llm.ollama import ollama_embed, ollama_model_complete
from lightrag.utils import setup_logger, EmbeddingFunc
from tqdm import tqdm

from db.database import SessionLocal
from db.models import Note, Blog, Photo
from rag_engine.formatters.formatter import format_note, format_blog, format_photo
from server import config

setup_logger("lightrag", level="INFO")

WORKING_DIR = "../rag_storage"
if not os.path.exists(WORKING_DIR):
    os.mkdir(WORKING_DIR)


async def initialize_rag():
    rag = LightRAG(
        working_dir=WORKING_DIR,
        llm_model_func=ollama_model_complete,  # 使用Ollama模型进行文本生成
        llm_model_name=config.BASE_MODEL,  # 您的模型名称
        llm_model_kwargs={
            "host": config.OPENAI_BASE_URL,
            "options": {"num_ctx": 8192},
            "timeout": int(os.getenv("TIMEOUT", "6000")),
        },
        # 使用Ollama嵌入函数
        embedding_func=EmbeddingFunc(
            embedding_dim=768,
            max_token_size=8192,
            func=lambda texts: ollama_embed(
                texts,
                embed_model=config.EMBEDDING_MODEL,
                host=config.OPENAI_BASE_URL,
                timeout=6000
            )
        ),
        kv_storage="PGKVStorage",
        vector_storage="PGVectorStorage",
        graph_storage="Neo4JStorage",
        doc_status_storage="PGDocStatusStorage",
    )
    await rag.initialize_storages()
    await initialize_pipeline_status()
    return rag


async def build_index():
    session = SessionLocal()

    # 初始化RAG实例
    rag = await initialize_rag()

    # Note
    notes = session.query(Note).all()
    print(f"⏰ 开始针对 Notes 做RAG")
    for note in tqdm(notes, desc="Notes"):
        text = format_note(note)
        await rag.ainsert(text, file_paths=getattr(note, 'file_path', None))
    print(f"✅ Notes 总结完成")

    # Blog
    blogs = session.query(Blog).all()
    print(f"⏰ 开始针对 Blogs 做RAG")
    for blog in tqdm(blogs, desc="Blogs"):
        text = format_blog(blog)
        await rag.ainsert(text, file_paths=getattr(blog, 'file_path', None))
    print(f"✅ Blogs 总结完成")

    # Photo
    photos = session.query(Photo).all()
    print(f"⏰ 开始针对 Photos 做RAG")
    for photo in tqdm(photos, desc="Photos"):
        text = format_photo(photo)
        await rag.ainsert(text, file_paths=getattr(photo, 'file_path', None))
    print(f"✅ Photos 总结完成")

    session.close()


if __name__ == "__main__":
    import asyncio

    asyncio.run(build_index())
