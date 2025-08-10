# rag_engine/config.py
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://root:root@localhost:5432/alfred")

# —— LLM & Embedding ——
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL","127.0.0.1:11434")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "ollama")

SUMMARIZE_MODEL = os.getenv("SUMMARIZE_MODEL", "gemma3:4b")
BASE_MODEL = os.getenv("BASE_MODEL", "gemma3:4b")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "bge-m3:latest")
VISION_LLM_MODEL = os.getenv("VISION_LLM_MODEL", "gemma3:4b")

# —— 数据路径（Path 对象方便做 / 拼接，但后续传第三方库时记得 str(...)） ——
NOTES_DIR = os.getenv("NOTES_DIR", "/Users/yueyong/alfred_test_data/notes")
BLOGS_DIR = os.getenv("BLOGS_DIR", "/Users/yueyong/alfred_test_data/blogs")
PHOTOS_DIR = os.getenv("PHOTOS_DIR", "/Users/yueyong/alfred_test_data/photos")
REDNOTE_DIR= os.getenv("REDNOTE_DIR", "/Users/yueyong/alfred_test_data/rednotes")

# —— Chunk —— 
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 512))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 64))

API_SERVER_PORT = int(os.getenv("API_SERVER_PORT", 11435))

def load_rate_limit_config():
    """
    从.env文件加载速率限制配置
    如果环境变量不存在，返回默认值
    """
    load_dotenv()

    # 检查是否启用速率限制
    rate_limit_enabled = os.getenv('RATE_LIMIT_ENABLED', 'true').lower() == 'true'

    if not rate_limit_enabled:
        return {
            'enabled': False,
            'max_requests': float('inf'),  # 无限制
            'time_window': 1,
            'min_delay': 0,
            'max_delay': 0
        }

    return {
        'enabled': True,
        'max_requests': int(os.getenv('RATE_LIMIT_MAX_REQUESTS', '2')),
        'time_window': int(os.getenv('RATE_LIMIT_TIME_WINDOW', '1')),
        'min_delay': float(os.getenv('RATE_LIMIT_MIN_DELAY', '0.2')),  # 默认值改小一些
        'max_delay': float(os.getenv('RATE_LIMIT_MAX_DELAY', '0.5'))   # 默认值改小一些
    }