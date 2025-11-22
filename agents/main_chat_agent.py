"""Orchestrator runtime built on top of qwen-agent Router + Assistant."""

from __future__ import annotations

from typing import Dict, Iterator, List

import logging
from qwen_agent.agents import Assistant, Router

from agents.vl_agent import vision_assistant
from server import config
from tools import DailyHotTrendsTool, ForexRateTool, CurrentTimeTool, WeatherTool

logger = logging.getLogger("server.app")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

SYSTEM_PROMPT = (
    "你是 Alfred 的总协调 Agent，需要综合个人知识库、日常数据源以及各种工具来回答问题。"
    "在作答前应先判断是否需要调用可用工具。"
)


def build_agent() -> Router:
    """Build a router agent that dispatches between text and vision assistants."""
    router = Router(
        llm=_build_llm_cfg(),
        agents=[
            vision_assistant(),
            _build_general_assistant(),
        ],
        name="router",
        description="负责在通用对话与视觉理解助手之间路由。",
    )
    return router


def run_agent(messages: List[Dict]) -> str:
    """Run the orchestrator in non-streaming mode and return the final content string."""
    agent = build_agent()
    normalized = _normalize_messages(messages)
    responses = agent.run_nonstream(normalized)
    if not responses:
        return ""
    latest = _get_content(responses[-1])
    return latest or ""


def stream_agent(messages: List[Dict]) -> Iterator[str]:
    """Stream textual deltas from the orchestrator."""
    agent = build_agent()
    normalized = _normalize_messages(messages)
    logger.debug("_normalize_messages: %s", normalized)
    buffer = ""
    for chunk in agent.run(normalized):
        if not chunk:
            continue
        latest = _get_content(chunk[-1]) or ""
        if latest.startswith(buffer):
            delta = latest[len(buffer):]
        else:
            delta = latest
        buffer = latest
        if delta:
            yield delta


def _build_llm_cfg() -> Dict:
    return {
        "model": config.LLM_MODEL,
        "model_server": config.LLM_BASE_URL,
        "api_key": config.LLM_API_KEY,
        "generate_cfg": {
            "temperature": config.LLM_TEMPERATURE,
        },
    }


def _build_general_assistant() -> Assistant:
    # tools = default_tools()
    tool_instances = [
        DailyHotTrendsTool(),
        ForexRateTool(),
        CurrentTimeTool(),
        WeatherTool(),
    ]
    general_llm_cfg = {
        "model": config.LLM_MODEL,
        "model_server": config.LLM_BASE_URL,
        "api_key": config.LLM_API_KEY,
        "generate_cfg": {
            "temperature": config.LLM_TEMPERATURE,
        },
    }
    return Assistant(
        function_list=tool_instances,
        llm=general_llm_cfg,
        system_message=SYSTEM_PROMPT,
        name="general",
        description="通用助手，负责文本对话与工具调用。",
    )





def _normalize_messages(messages: List[Dict]) -> List[Dict]:
    """Convert OpenAI-style multimodal messages to qwen-agent schema."""
    normalized = []
    for msg in messages:
        content = msg.get("content")
        if isinstance(content, list):
            parts = []
            for part in content:
                if not isinstance(part, dict):
                    continue
                p_type = part.get("type")
                if p_type == "text":
                    parts.append({"text": part.get("text", "")})
                elif p_type in ("image_url", "image"):
                    url = None
                    image_info = part.get("image_url") or {}
                    if isinstance(image_info, dict):
                        url = image_info.get("url")
                    elif isinstance(image_info, str):
                        url = image_info
                    if not url and isinstance(part.get("image"), str):
                        url = part.get("image")
                    if url:
                        parts.append({"image": url})
                elif p_type in ("file", "input_file"):
                    file_val = None
                    file_info = part.get("file") or part.get("input_file")
                    if isinstance(file_info, dict):
                        file_val = (
                                file_info.get("url")
                                or file_info.get("path")
                                or file_info.get("data")
                                or file_info.get("content")
                        )
                    elif isinstance(file_info, str):
                        file_val = file_info
                    if file_val:
                        parts.append({"file": file_val})
                else:
                    # Already-normalized qwen style content items.
                    for key in ("text", "image", "file"):
                        if isinstance(part.get(key), str):
                            parts.append({key: part[key]})
                            break
            msg = {**msg, "content": parts}
        normalized.append(msg)
    return normalized


def _get_content(message) -> str:
    """Safely extract content from qwen Message or dict."""
    try:
        return message.content or ""
    except Exception:
        if isinstance(message, dict):
            return message.get("content") or ""
    return ""
