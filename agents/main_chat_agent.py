"""Orchestrator runtime built on top of qwen-agent Router + Assistant."""

from __future__ import annotations

import logging
from typing import Dict, Iterator, List

from qwen_agent.agents import Router
from qwen_agent.tools import WebSearch, CodeInterpreter

from agents.code_agent import code_assistant
from agents.image_gen_agent import image_gen_assistant
from agents.vl_agent import vision_assistant
from server import config
from tools.daily_hot import DailyHotTrendsTool
from tools.forex import ForexRateTool
from tools.hot_article import WebSummaryTool
from tools.time_tools import CurrentTimeTool
from tools.weather import WeatherTool

logger = logging.getLogger("server.app")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

SYSTEM_PROMPT = (
    "你是 Alfred 的总协调 Agent，需要综合个人知识库、日常数据源以及各种工具来回答问题。"
    "在作答前应先判断是否需要调用可用工具。"
)


def build_main_chat_agent() -> Router:
    """Build a router agent that dispatches between text and vision assistants."""
    route_llm_cfg = {
        "model": config.LLM_MODEL,
        "model_server": config.LLM_BASE_URL,
        "api_key": config.LLM_API_KEY,
        "generate_cfg": {
            "temperature": config.LLM_TEMPERATURE,
        },
    }

    tool_instances = [
        WeatherTool(),
        DailyHotTrendsTool(),
        WebSummaryTool(),
        ForexRateTool(),
        CurrentTimeTool(),
        WebSearch(),
        CodeInterpreter()
    ]

    router = Router(
        llm=route_llm_cfg,
        function_list=tool_instances,
        agents=[
            vision_assistant(),
            image_gen_assistant(),
            code_assistant()
        ],
        name="router",
        description="负责在通用对话与视觉理解助手之间路由。",
    )
    return router


def run_main_chat(messages: List[Dict]) -> str:
    """Run the orchestrator in non-streaming mode and return the final content string."""
    main_chat_agent = build_main_chat_agent()
    normalized = _normalize_messages(messages)
    responses = main_chat_agent.run_nonstream(normalized)
    if not responses:
        return ""
    latest = _get_content(responses[-1])
    return latest or ""


def stream_agent(messages: List[Dict]) -> Iterator[str]:
    """Stream textual deltas from the orchestrator."""
    agent = build_main_chat_agent()
    normalized = _normalize_messages(messages)
    # logger.info("_normalize_messages: %s", normalized)
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


def _normalize_messages(messages: List[Dict]) -> List[Dict]:
    """Convert OpenAI-style multimodal messages to qwen-agent schema."""
    normalized = []
    for msg in messages:
        parts = []

        def _extract_image_url(obj) -> str | None:
            url = None
            if isinstance(obj, str):
                url = obj
            elif isinstance(obj, dict):
                info = obj.get("image_url") or obj.get("image") or obj
                if isinstance(info, dict):
                    url = (
                            info.get("url")
                            or info.get("data")
                            or info.get("base64")
                            or info.get("content")
                            or info.get("path")
                    )
                elif isinstance(info, str):
                    url = info
            return url

        def _extract_file_val(obj) -> str | None:
            if isinstance(obj, str):
                return obj
            if isinstance(obj, dict):
                info = obj.get("file") or obj.get("input_file") or obj
                if isinstance(info, dict):
                    return (
                            info.get("url")
                            or info.get("path")
                            or info.get("data")
                            or info.get("content")
                    )
                if isinstance(info, str):
                    return info
            return None

        content = msg.get("content")
        if isinstance(content, list):
            for part in content:
                if not isinstance(part, dict):
                    continue
                p_type = part.get("type")
                if p_type == "text":
                    parts.append({"text": part.get("text", "")})
                elif p_type in ("image_url", "image"):
                    url = _extract_image_url(part)
                    if url:
                        parts.append({"image": url})
                elif p_type in ("file", "input_file"):
                    file_val = _extract_file_val(part)
                    if file_val:
                        parts.append({"file": file_val})
                else:
                    # Already-normalized qwen style content items.
                    for key in ("text", "image", "file"):
                        if isinstance(part.get(key), str):
                            parts.append({key: part[key]})
                            break
        elif isinstance(content, str):
            if content:
                parts.append({"text": content})

        # message-level images/files (e.g., {"content": "xxx", "images": [...]})
        for image in msg.get("images") or []:
            url = _extract_image_url(image)
            if url:
                parts.append({"image": url})
        for file_item in msg.get("files") or []:
            val = _extract_file_val(file_item)
            if val:
                parts.append({"file": val})

        # Create new message without the original images/files fields to avoid double processing
        new_msg = {k: v for k, v in msg.items() if k not in ("images", "files")}
        new_msg["content"] = parts
        normalized.append(new_msg)
    return normalized


def _get_content(message) -> str:
    """Safely extract content from qwen Message or dict."""
    try:
        return message.content or ""
    except Exception:
        if isinstance(message, dict):
            return message.get("content") or ""
    return ""
