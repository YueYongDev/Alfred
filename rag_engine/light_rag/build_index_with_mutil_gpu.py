import asyncio
import os
import argparse
from typing import List

from lightrag import LightRAG
from lightrag.llm.ollama import ollama_embed, ollama_model_complete
from lightrag.utils import EmbeddingFunc
from lightrag.kg.shared_storage import initialize_pipeline_status
from sqlalchemy import select

from db.database import SessionLocal
from db.models import Photo
from rag_engine.formatters.formatter import format_photo
from server import config

# ----------- 配置 -----------
MAX_CONCURRENCY = int(os.getenv("INDEX_MAX_CONCURRENCY", "12"))
DB_PAGE_SIZE = int(os.getenv("INDEX_DB_PAGE_SIZE", "500"))
TIMEOUT_SEC = int(os.getenv("OLLAMA_TIMEOUT_SEC", "120"))
WORKING_DIR = os.getenv("RAG_WORKING_DIR", "./rag_storage")

# 单实例使用的 Ollama 地址（通过环境变量覆盖）
OLLAMA_HOST = os.getenv("OLLAMA_BASE_URL", getattr(config, "OLLAMA_INSTANCE_0", "http://127.0.0.1:11434"))
EMBED_HOST = os.getenv("OLLAMA_EMBEDDING_URL", OLLAMA_HOST)


# ----------- RAG 初始化 -----------
async def mk_rag() -> LightRAG:
    rag = LightRAG(
        working_dir=WORKING_DIR,
        llm_model_func=ollama_model_complete,
        llm_model_name=config.OLLAMA_BASE_MODEL,
        llm_model_kwargs={
            "host": OLLAMA_HOST,
            "options": {"num_ctx": 8192},
            "timeout": TIMEOUT_SEC,
        },
        embedding_func=EmbeddingFunc(
            embedding_dim=768,
            max_token_size=8192,
            func=lambda texts: ollama_embed(
                texts,
                embed_model=config.OLLAMA_EMBEDDING_MODEL,
                host=EMBED_HOST,
                timeout=TIMEOUT_SEC,
            ),
        ),
        kv_storage="PGKVStorage",
        vector_storage="PGVectorStorage",
        graph_storage="Neo4JStorage",
        doc_status_storage="PGDocStatusStorage",
        # 如果不想看到 "Rerank is enabled..." 警告，可以加上：
        # enable_rerank=False,
        # rerank_top_k=0,
    )
    await rag.initialize_storages()
    # 初始化 pipeline 状态（内部会保证 history_messages 等 key 存在）
    await initialize_pipeline_status()
    return rag


# ----------- DB 流式读取 -----------
def stream_photos():
    with SessionLocal() as s:
        offset = 0
        while True:
            batch = s.execute(select(Photo).offset(offset).limit(DB_PAGE_SIZE)).scalars().all()
            if not batch:
                break
            yield batch
            offset += DB_PAGE_SIZE


# ----------- 索引主逻辑（按分片过滤） -----------
async def index_shard(shard: int, shards: int):
    rag = await mk_rag()
    sem = asyncio.Semaphore(MAX_CONCURRENCY)
    failures: List[tuple] = []

    async def insert_one(p: Photo):
        async with sem:
            try:
                text = format_photo(p)
                await rag.ainsert(
                    text,
                    file_paths=getattr(p, "file_path", None),
                    doc_id=f"photo:{p.id}",  # 幂等
                    metadata={"type": "photo", "photo_id": p.id},
                )
            except Exception as e:
                failures.append((p.id, str(e)))

    for page in stream_photos():
        mine = [p for p in page if (p.id % shards) == shard]
        if not mine:
            continue
        await asyncio.gather(*(insert_one(p) for p in mine))

    if failures:
        print(f"⚠️ 分片 {shard}/{shards} 失败 {len(failures)} 条，前 5 条：")
        for pid, err in failures[:5]:
            print(f"   - photo_id={pid}: {err}")


# ----------- CLI -----------
def parse_args():
    ap = argparse.ArgumentParser(description="Build LightRAG index (single instance, sharded by modulo).")
    ap.add_argument("--shard", type=int, default=0, help="当前进程负责的分片号，从 0 开始")
    ap.add_argument("--shards", type=int, default=2, help="总分片数")
    return ap.parse_args()


async def main():
    args = parse_args()
    assert 0 <= args.shard < args.shards, "shard 必须满足 0 <= shard < shards"
    print(f"🚀 启动索引：分片 {args.shard}/{args.shards}，Ollama={OLLAMA_HOST}，并发={MAX_CONCURRENCY}")
    await index_shard(args.shard, args.shards)
    print("✅ 本分片完成")


if __name__ == "__main__":
    asyncio.run(main())