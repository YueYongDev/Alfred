# rag/rag_service.py

from llama_index.core import ServiceContext, VectorStoreIndex, SimpleDirectoryReader
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama
from llama_index.vector_stores.postgres import PGVectorStore


class RagService:
    """
    RAG 服务类，封装向量检索 + LLM 推理功能。
    """

    def __init__(
            self,
            pg_host: str = "localhost",
            pg_port: str = "5432",
            pg_db: str = "alfred",
            pg_user: str = "root",
            pg_password: str = "root",
            table_name: str = "note",
            embed_dim: int = 768,
            embedding_model: str = "mxbai-embed-large",
            llm_model: str = "llama3.1",
            ollama_url: str = "http://localhost:11434",
    ):
        # 初始化向量模型与 LLM
        self.embed_model = OllamaEmbedding(model_name=embedding_model)
        self.llm = Ollama(model=llm_model, base_url=ollama_url)

        # 构造向量存储
        self.vector_store = PGVectorStore.from_params(
            host=pg_host,
            port=pg_port,
            database=pg_db,
            user=pg_user,
            password=pg_password,
            table_name=table_name,
            embed_dim=embed_dim,
        )

        # 环境上下文
        self.service_context = ServiceContext.from_defaults(
            embed_model=self.embed_model,
            llm=self.llm
        )

        # 创建索引（首次运行时创建，后续同表可共用）
        # 如果数据量大，建议 extract+embed阶段单独构建，然后这里直接加载
        self.index = VectorStoreIndex.from_vector_store(
            self.vector_store,
            service_context=self.service_context
        )
        self.query_engine = self.index.as_query_engine(similarity_top_k=4)

    def query(self, question: str) -> str:
        """
        返回 RAG 查询的文本回答。
        """
        resp = self.query_engine.query(question)
        return resp.response
