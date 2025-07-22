from llama_index.core import ChatPromptTemplate
from llama_index.core.base.llms.types import MessageRole, ChatMessage
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama

from rag_engine import config


def get_llm():
    return Ollama(
        base_url=config.OPENAI_BASE_URL,
        model=config.BASE_MODEL,
        request_timeout=600,
    )


def get_summarize_llm():
    return Ollama(
        base_url=config.OPENAI_BASE_URL,
        model=config.BASE_MODEL,
        request_timeout=600,
        json_mode=True,
    )


def get_extractor_llm():
    return Ollama(
        base_url=config.OPENAI_BASE_URL,
        model=config.EXTRACTION_MODEL,
        request_timeout=600,
        temperature=0.1,  # 降低随机性
        top_k=20,  # 限制候选词数量
        top_p=0.9,  # 核采样
        num_predict=256,  # 限制输出长度
        num_ctx=2048,  # 上下文长度
    )


def get_embed_model():
    return OllamaEmbedding(
        base_url=config.OPENAI_BASE_URL,
        model_name=config.EMBEDDING_MODEL,
        request_timeout=600,
    )


def get_vision_llm():
    return Ollama(
        base_url=config.OPENAI_BASE_URL,
        model=config.VISION_LLM_MODEL,
        timeout=600,
        json_mode=True
    )
