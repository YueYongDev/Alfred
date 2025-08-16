# rag_engine/vector_rag/query_engine.py

import asyncio
import inspect
import os

from lightrag import LightRAG, QueryParam
from lightrag.kg.shared_storage import initialize_pipeline_status
from lightrag.llm.ollama import ollama_embed, ollama_model_complete
from lightrag.utils import setup_logger, EmbeddingFunc

from server import config

setup_logger("lightrag", level="INFO")

WORKING_DIR = "../rag_storage"


async def initialize_rag():
    rag = LightRAG(
        working_dir=WORKING_DIR,
        llm_model_func=ollama_model_complete,  # 使用Ollama模型进行文本生成
        llm_model_name=config.OLLAMA_BASE_MODEL,  # 您的模型名称
        llm_model_kwargs={
            "host": config.OLLAMA_BASE_URL,
            "options": {"num_ctx": 8192},
            "timeout": int(os.getenv("TIMEOUT", "300")),
        },
        # 使用Ollama嵌入函数
        embedding_func=EmbeddingFunc(
            embedding_dim=768,
            max_token_size=8192,
            func=lambda texts: ollama_embed(
                texts,
                embed_model=config.OLLAMA_EMBEDDING_MODEL,
                host=config.OLLAMA_EMBEDDING_URL,
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


def answer_question_sync(question, mode="hybrid"):
    async def _ask():
        rag = await initialize_rag()
        await rag.aclear_cache()
        resp = await rag.aquery(
            question,
            param=QueryParam(mode=mode, stream=False),
        )
        await rag.finalize_storages()
        return resp

    return asyncio.run(_ask())


def answer_question_stream(question, mode="hybrid"):
    async def _ask():
        rag = await initialize_rag()
        await rag.aclear_cache()
        resp = await rag.aquery(
            question,
            param=QueryParam(mode=mode, stream=True),
        )
        if inspect.isasyncgen(resp):
            async for chunk in resp:
                if chunk:
                    yield chunk
        else:
            yield resp
        await rag.finalize_storages()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    gen = _ask()
    try:
        while True:
            chunk = loop.run_until_complete(gen.__anext__())
            yield chunk
    except StopAsyncIteration:
        pass
    finally:
        loop.close()


if __name__ == "__main__":
    q = "作者对API网关的态度是什么"
    # for chunk in answer_question_stream(q):
    #     print("Streamed chunk:", chunk)
    print(answer_question_sync(q))
