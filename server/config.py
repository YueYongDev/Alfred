"""Minimal configuration for Alfred core (agent + API)."""

import os
from dotenv import load_dotenv

load_dotenv()

# —— LLM (OpenAI-compatible) ——
# 统一用 openai 格式，既可指向本地/远程 Ollama，也可指向 OpenAI/其他兼容服务。
LLM_MODEL = os.getenv("LLM_MODEL", "qwen3:latest")
LLM_VL_MODEL = os.getenv("LLM_VL_MODEL", "qwen3-vl:4b")
LLM_CODE_MODEL = os.getenv("LLM_CODE_MODEL", "qwen3-coder-plus")
LLM_ROUTE_MODEL = os.getenv("LLM_ROUTE_MODEL", "qwen3:1.7b")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://127.0.0.1:11434/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "ollama")  # Ollama 兼容接口可用任意非空值
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))

# —— External services ——
DAILY_HOT_API_BASE = os.getenv("DAILY_HOT_API_BASE", "http://localhost:6688")
WEB_SUMMARY_API = os.getenv("WEB_SUMMARY_API", "http://127.0.0.1:8001/summarize")

# —— API Server ——
API_SERVER_PORT = int(os.getenv("API_SERVER_PORT", 11435))
