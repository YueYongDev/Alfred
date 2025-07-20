from llama_index.core.bridge.pydantic import BaseModel
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama

from rag_engine import config


def get_llm():
    return Ollama(
        model=config.BASE_MODEL,
        request_timeout=300,
    )


def get_extractor_llm():
    return Ollama(
        model=config.EXTRACTION_MODEL,
        request_timeout=300,
        json_mode=True
    )


def get_embed_model():
    return OllamaEmbedding(
        model_name=config.EMBEDDING_MODEL,
        request_timeout=300,
    )


def get_vision_llm():

    return Ollama(
        model=config.VISION_LLM_MODEL,
        timeout=300,
        json_mode=True
    )
