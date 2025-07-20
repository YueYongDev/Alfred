# server/app.py
# ────────────────────────────────────────────────
#  启动：python -m server.app
#  OpenAI 兼容接口：/v1/chat/completions
# ────────────────────────────────────────────────
import json
import time
import uuid
from typing import List, Optional

import chromadb
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict

from llama_index.core import Settings, StorageContext, load_index_from_storage
from llama_index.core.retrievers import RouterRetriever
from llama_index.core.tools import RetrieverTool
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.vector_stores.chroma import ChromaVectorStore

from rag_engine import config
from rag_engine.providers import get_llm, get_embed_model

# ────────────────────────── FastAPI init ──────────────────────────
app = FastAPI(title="Alfred Hybrid-RAG API", version="0.3")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
    allow_credentials=True,
)

# ─────────────── 全局 LLM / Embedding，避免默认找 OpenAI ───────────────
Settings.llm = get_llm()
Settings.embed_model = get_embed_model()

# ─────────────── Knowledge-Graph 索引（读取磁盘） ───────────────
kg_ctx = StorageContext.from_defaults(persist_dir=str(config.GRAPH_DB_DIR))
kg_index = load_index_from_storage(kg_ctx)
graph_ret = kg_index.as_retriever(depth=2)

# ───────── Vector 索引 (Chroma) ─────────
chromadb_client = chromadb.PersistentClient(path=str(config.VECTOR_DB_DIR))
collection = chromadb_client.get_or_create_collection("alfred_vectors")
vec_store = ChromaVectorStore(chroma_collection=collection)

vec_ctx = StorageContext.from_defaults(        # ← 删除 docstore=kg_ctx.docstore
    persist_dir=str(config.VECTOR_DB_DIR),
    vector_store=vec_store,
)
vec_index = load_index_from_storage(vec_ctx)
vector_ret = vec_index.as_retriever(similarity_top_k=8)

# ─────────────── RouterRetriever 组装 ───────────────
graph_tool = RetrieverTool.from_defaults(
    graph_ret, name="graph",
    description="基于知识图谱的检索，适合问及实体关系、属性等结构化问题")
vector_tool = RetrieverTool.from_defaults(
    vector_ret, name="vector",
    description="向量语义检索，适合全文内容相似度查询")

router_ret = RouterRetriever.from_defaults(
    retriever_tools=[graph_tool, vector_tool],
    llm=Settings.llm,
    select_multi=False       # 命中一个就走一个
)

# RouterRetriever → QueryEngine（支持流式）
query_engine = RetrieverQueryEngine.from_args(
    retriever=router_ret, llm=Settings.llm, streaming=True
)

# ─────────────── OpenAI-style Request schema ───────────────


class ChatMessage(BaseModel):
    role: str
    content: Optional[str] = ""


class ChatReq(BaseModel):
    model: str
    messages: List[ChatMessage]
    stream: Optional[bool] = False
    model_config = ConfigDict(extra="allow")    # 忽略前端可能新增的字段

# ─────────────── /v1/chat/completions endpoint ───────────────


@app.post("/v1/chat/completions")
async def chat(req: ChatReq):
    prompt = "\n".join(m.content for m in req.messages
                       if m.role == "user" and m.content)

    # ---------- Stream ----------
    if req.stream:
        def gen():
            resp = query_engine.query(prompt)
            # llama-index streaming Response 有 .generator
            tokens = getattr(resp, "response_gen", None) or getattr(
                resp, "generator", None)
            if tokens is None:          # 如果依然拿不到，就退化为一次性返回
                tokens = [str(resp)]
            for tok in tokens:
                payload = {
                    "id": f"chatcmpl-{uuid.uuid4()}",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": req.model,
                    "choices": [{
                        "delta": {"content": str(tok)},
                        "index": 0,
                        "finish_reason": None
                    }]
                }
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(gen(), media_type="text/event-stream")

    # ---------- Non-stream ----------
    resp = query_engine.query(prompt)
    data = {
        "id": f"chatcmpl-{uuid.uuid4()}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": req.model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": str(resp)},
            "finish_reason": "stop"
        }],
        # 如需 token 计费可在此补充
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    }
    return JSONResponse(content=data)

# ────────────────────────── main ──────────────────────────
if __name__ == "__main__":
    uvicorn.run("server.app:app", host="0.0.0.0",
                port=config.API_SERVER_PORT, reload=True)
