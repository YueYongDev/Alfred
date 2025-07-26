import asyncio
import os

import nest_asyncio
from lightrag import LightRAG
from lightrag.llm.ollama import ollama_model_complete, ollama_embed, _ollama_model_if_cache
from lightrag.utils import EmbeddingFunc
from raganything import RAGAnything

from server import config

nest_asyncio.apply()


async def load_existing_lightrag():
    # 首先，创建或加载现有的 LightRAG 实例
    lightrag_working_dir = "./existing_lightrag_storage"

    # 检查是否存在之前的 LightRAG 实例
    if os.path.exists(lightrag_working_dir) and os.listdir(lightrag_working_dir):
        print("✅ Found existing LightRAG instance, loading...")
    else:
        print("❌ No existing LightRAG instance found, will create new one")

    # 使用您的配置创建/加载 LightRAG 实例
    lightrag_instance = LightRAG(
        working_dir=lightrag_working_dir,
        llm_model_func=ollama_model_complete,  # 使用Ollama模型进行文本生成
        llm_model_name=config.BASE_MODEL,  # 您的模型名称
        llm_model_kwargs={
            "host": config.OPENAI_BASE_URL,
            "options": {"num_ctx": 8192},
            "timeout": int(os.getenv("TIMEOUT", "300")),
        },
        # 使用Ollama嵌入函数
        embedding_func=EmbeddingFunc(
            embedding_dim=768,
            max_token_size=8192,
            func=lambda texts: ollama_embed(
                texts,
                embed_model=config.EMBEDDING_MODEL,
                host=config.OPENAI_BASE_URL,
            )
        ),
        kv_storage="PGKVStorage",
        vector_storage="PGVectorStorage",
        graph_storage="Neo4JStorage",
        doc_status_storage="PGDocStatusStorage",
    )

    # 初始化存储（如果有现有数据，这将加载现有数据）
    await lightrag_instance.initialize_storages()

    # 现在使用现有的 LightRAG 实例初始化 RAGAnything
    rag = RAGAnything(
        lightrag=lightrag_instance,  # 传递现有的 LightRAG 实例
        # 仅需要视觉模型用于多模态处理
        vision_model_func=lambda prompt, system_prompt=None, history_messages=[], image_data=None,
                                 **kwargs: _ollama_model_if_cache(
            config.BASE_MODEL,
            "",
            system_prompt=None,
            history_messages=[],
            messages=[
                {"role": "system", "content": system_prompt} if system_prompt else None,
                {"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                ]} if image_data else {"role": "user", "content": prompt}
            ],
            api_key="your-api-key",
            **kwargs,
        ) if image_data else _ollama_model_if_cache(
            config.VISION_LLM_MODEL,
            prompt,
            system_prompt=system_prompt,
            history_messages=history_messages,
            api_key="your-api-key",
            **kwargs,
        )
        # 注意：working_dir、llm_model_func、embedding_func 等都从 lightrag_instance 继承
    )

    # 查询现有的知识库
    # result = rag.query_with_multimodal(
    #     "区块链和麻将有什么关系",
    #     mode="naive"
    # )
    # print("Query result:", result)

    # 向现有的 LightRAG 实例添加新的多模态文档
    await rag.process_document_complete(
        file_path="/Users/yueyong/Downloads/你看那个区块链，像不像我借你的二百元.pdf",
        output_dir="./output",
    )


if __name__ == "__main__":
    asyncio.run(load_existing_lightrag())
