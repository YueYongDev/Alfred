from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama

from server import config


def get_llm():
    return Ollama(
        base_url=config.OLLAMA_BASE_URL,
        model=config.OLLAMA_BASE_MODEL,
        request_timeout=6000,
        tools=False,
    )


def get_summarize_llm():
    return Ollama(
        base_url=config.OLLAMA_SUMMARIZE_URL,
        model=config.OLLAMA_SUMMARIZE_MODEL,
        request_timeout=6000,
        json_mode=True,
        thinking=False
    )


def get_embed_model():
    return OllamaEmbedding(
        base_url=config.OLLAMA_EMBEDDING_URL,
        model_name=config.OLLAMA_EMBEDDING_MODEL,
        request_timeout=6000,
    )


def get_vision_llm():
    return Ollama(
        base_url=config.OLLAMA_VISION_URL,
        model=config.OLLAMA_VISION_MODEL,
        request_timeout=6000,
        json_mode=True
    )
