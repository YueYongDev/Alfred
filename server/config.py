# rag_engine/config.py
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv()

# —— LLM & Embedding ——
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY", "ollama")

EXTRACTION_MODEL = os.getenv("EXTRACTION_MODEL", "gemma3:1b")
BASE_MODEL       = os.getenv("BASE_MODEL",       "gemma3:4b")
EMBEDDING_MODEL  = os.getenv("EMBEDDING_MODEL",  "bge-m3:latest")
VISION_LLM_MODEL = os.getenv("VISION_LLM_MODEL", "gemma3:4b")

# —— 数据路径（Path 对象方便做 / 拼接，但后续传第三方库时记得 str(...)） ——
NOTES_DIR   = Path(os.getenv("NOTES_DIR",   BASE_DIR / "data/notes")).resolve()
BLOGS_DIR    = Path(os.getenv("BLOGS_DIR",    BASE_DIR / "data/blog")).resolve()
PHOTOS_DIR  = Path(os.getenv("PHOTOS_DIR",  BASE_DIR / "data/photos")).resolve()

GRAPH_DB_DIR  = Path(os.getenv("GRAPH_DB_DIR",  BASE_DIR / "storage/graph_db")).resolve()
VECTOR_DB_DIR = Path(os.getenv("VECTOR_DB_DIR", BASE_DIR / "storage/vector_db")).resolve()

# —— Chunk —— 
CHUNK_SIZE     = int(os.getenv("CHUNK_SIZE", 512))
CHUNK_OVERLAP  = int(os.getenv("CHUNK_OVERLAP", 64))

API_SERVER_PORT = int(os.getenv("API_SERVER_PORT", 11435))