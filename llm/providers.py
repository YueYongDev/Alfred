from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama

from server import config


def get_llm():
    return Ollama(
        base_url=config.OPENAI_BASE_URL,
        model=config.BASE_MODEL,
        request_timeout=600,
        tools=False,
    )


def get_summarize_llm():
    return Ollama(
        base_url=config.OPENAI_BASE_URL,
        model=config.SUMMARIZE_MODEL,
        request_timeout=6000,
        json_mode=True,
        thinking=False
    )


def get_embed_model():
    return OllamaEmbedding(
        base_url=config.OPENAI_BASE_URL,
        model_name=config.EMBEDDING_MODEL,
        request_timeout=6000,
    )


def get_vision_llm():
    return Ollama(
        base_url=config.OPENAI_BASE_URL,
        model=config.VISION_LLM_MODEL,
        timeout=1200,
        json_mode=True
    )
