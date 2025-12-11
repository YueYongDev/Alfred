import json
import logging
import uuid
from pathlib import Path
from typing import Any, Dict, List, Tuple

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from agents.core.messaging.chat_request import (Body, ChatRequest, Header,
                                                Message, Parameters,
                                                SystemParams)
# 添加必要的导入
from agents.routers.main_chat_router import MainChatRouter
from server import config

logger = logging.getLogger("server.app")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def serve_frontend():
    """Serve the main SPA entry."""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/agents")
async def list_agents():
    metadata = get_agent_metadata()
    return JSONResponse(metadata["agents"])


@app.get("/api/tools")
async def list_tools():
    metadata = get_agent_metadata()
    return JSONResponse(metadata["tools"])

def _tool_meta(tool: Any, agent_name: str) -> Dict[str, Any]:
    """
    提取工具元数据信息

    Args:
        tool: 工具对象
        agent_name: 所属agent名称

    Returns:
        Dict[str, Any]: 工具元数据字典
    """
    try:
        # 获取工具名称
        name = getattr(tool, 'name', str(tool.__class__.__name__))

        # 获取工具描述
        description = getattr(tool, 'description', '')
        if not description and hasattr(tool, '__doc__'):
            description = tool.__doc__ or ''

        # 获取工具参数
        parameters = getattr(tool, 'parameters', {})
        if not parameters and hasattr(tool, 'function'):
            # 尝试从 function 属性获取参数信息
            function_info = tool.function
            if isinstance(function_info, dict):
                parameters = function_info.get('parameters', {})

        return {
            "name": name,
            "description": description.strip() if description else "",
            "parameters": parameters,
            "agent": agent_name
        }
    except Exception as e:
        logger.warning(f"Failed to extract metadata for tool {tool}: {e}")
        return {
            "name": str(tool.__class__.__name__),
            "description": "",
            "parameters": {},
            "agent": agent_name
        }

def get_agent_metadata() -> Dict[str, Any]:
    """Return metadata about available agents and tools (with per-agent mapping)."""
    # 创建一个临时的ChatRequest用于初始化router
    from agents.core.messaging.chat_request import ChatRequest, Header, Body, Message
    import uuid

    temp_request = ChatRequest(
        header=Header(
            reqId=str(uuid.uuid4()),
            sessionId=f"metadata_{uuid.uuid4()}"
        ),
        body=Body(messages=[])
    )

    router = MainChatRouter(temp_request)
    # 创建bot实例
    router._create_bot()

    agents_data: List[Dict[str, Any]] = []
    tools_data: List[Dict[str, Any]] = []

    # 获取router中的agents
    if hasattr(router, 'bot') and hasattr(router.bot, 'agents'):
        agent_list = router.bot.agents
    else:
        # 如果没有agents属性，返回空数据
        agent_list = []

    for agent in agent_list:

        tool_list = []
        if hasattr(agent, "function_list"):
            tool_list = agent.function_list
        elif hasattr(agent, "function_map"):
            tool_list = list(agent.function_map.values())
        else:
            tool_list = (
                    getattr(agent, "function", None)
                    or getattr(agent, "tools", None)
                    or []
            )
        agent_tools = []
        for tool in tool_list:
            meta = _tool_meta(tool, agent.name)
            agent_tools.append(meta)
            tools_data.append(meta)

        agents_data.append(
            {
                "name": getattr(agent, "name", "agent"),
                "description": getattr(agent, "description", ""),
                "tools": agent_tools,
            }
        )

    for tool in getattr(router, "attached_tools", []):
        tools_data.append(_tool_meta(tool, "router"))

    return {
        "agents": agents_data,
        "tools": tools_data,
    }

def format_openai_stream_delta(delta_text: str):
    # 构造符合 OpenAI Stream 格式的单个 chunk
    data = {
        "choices": [
            {
                "delta": {"content": delta_text},
                "index": 0,
                "finish_reason": None,
            }
        ],
        "object": "chat.completion.chunk",
    }
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _find_latest_user(messages: List[Dict[str, Any]]) -> Tuple[int, Dict[str, Any] | None]:
    for idx in range(len(messages) - 1, -1, -1):
        msg = messages[idx]
        if isinstance(msg, dict) and msg.get("role") == "user":
            return idx, msg
    return -1, None


def _ensure_list_content(content: Any) -> List[Dict[str, Any]]:
    if isinstance(content, list):
        return [part for part in content if isinstance(part, dict)]
    if isinstance(content, str):
        return [{"type": "text", "text": content}] if content else []
    return []


def _image_part_from_payload(image: Any) -> Dict[str, Any] | None:
    url = None
    if isinstance(image, str):
        url = image
    elif isinstance(image, dict):
        url = (
                image.get("url")
                or image.get("data")
                or image.get("base64")
                or image.get("content")
                or image.get("path")
        )
    if url:
        return {"type": "image_url", "image_url": {"url": url}}
    return None


def _file_part_from_payload(file_item: Any) -> Dict[str, Any] | None:
    value = None
    if isinstance(file_item, str):
        value = file_item
    elif isinstance(file_item, dict):
        value = (
                file_item.get("url")
                or file_item.get("path")
                or file_item.get("data")
                or file_item.get("content")
        )
    if value:
        return {"type": "file", "file": value}
    return None


def _attach_media(messages: List[Dict[str, Any]], body: Dict[str, Any]) -> List[Dict[str, Any]]:
    # Check if messages already contain images/files at message level
    # If they do, we don't need to attach from top-level body
    has_message_level_media = any(
        msg.get("images") or msg.get("files")
        for msg in messages
        if isinstance(msg, dict) and msg.get("role") == "user"
    )

    if has_message_level_media:
        # Messages already have media at message level, return as-is
        return messages

    # Fall back to legacy behavior: attach from top-level body
    files = body.get("files") or []
    images = body.get("images") or []
    if not files and not images:
        return messages

    merged = list(messages)
    idx, user_msg = _find_latest_user(merged)
    if idx < 0 or not isinstance(user_msg, dict):
        return merged

    content_parts = _ensure_list_content(user_msg.get("content"))
    for image in images:
        part = _image_part_from_payload(image)
        if part:
            content_parts.append(part)
    for file_item in files:
        part = _file_part_from_payload(file_item)
        if part:
            content_parts.append(part)

    merged[idx] = {**user_msg, "content": content_parts}
    return merged


def _log_request_summary(body: Dict[str, Any]) -> None:
    messages = body.get("messages") or []
    files = body.get("files") or []
    images = body.get("images") or []
    _, user_msg = _find_latest_user(messages)
    preview = ""
    if isinstance(user_msg, dict):
        content = user_msg.get("content")
        if isinstance(content, str):
            preview = content[:200]
        elif isinstance(content, list):
            texts = [
                part.get("text", "")
                for part in content
                if isinstance(part, dict) and part.get("type") == "text"
            ]
            preview = " | ".join(t for t in texts if t)[:200]
    logger.info(
        "chat request: stream=%s messages=%s files=%s images=%s preview=%s",
        body.get("stream", False),
        messages,
        len(files),
        len(images),
        preview,
    )
    if files or images:
        logger.info("raw files payload: %s", files)
        logger.info("raw images payload: %s", images)


def _normalize_openai_content(content: Any) -> Any:
    """Convert OpenAI style content to the internal multimodal structure."""
    if isinstance(content, list):
        parts: List[Any] = []
        for item in content:
            if isinstance(item, dict):
                ctype = item.get("type")
                if ctype == "text":
                    if item.get("text"):
                        parts.append({"text": item["text"]})
                    continue
                if ctype == "image_url":
                    image_obj = item.get("image_url") or {}
                    url = None
                    if isinstance(image_obj, dict):
                        url = (
                            image_obj.get("url")
                            or image_obj.get("data")
                            or image_obj.get("base64")
                            or image_obj.get("content")
                        )
                    elif isinstance(image_obj, str):
                        url = image_obj
                    if url:
                        parts.append({"image": url})
                    continue
                # Fallback for already-normalized dicts
                if "text" in item or "image" in item or "file" in item:
                    parts.append(item)
                    continue
            elif isinstance(item, str):
                parts.append(item)
        return parts
    return content


def _build_chat_request_from_openai_payload(body: Dict[str, Any]) -> ChatRequest:
    """
    将 OpenAI 兼容的请求体转换为内部 ChatRequest 结构。
    """
    req_id = (
        body.get("req_id")
        or body.get("id")
        or body.get("request_id")
        or str(uuid.uuid4())
    )
    session_id = (
        body.get("session_id")
        or body.get("conversation_id")
        or body.get("user")
        or req_id
    )
    stream = body.get("stream", True)

    raw_messages: List[Dict[str, Any]] = []
    for msg in body.get("messages", []) or []:
        if not isinstance(msg, dict):
            continue
        role = msg.get("role")
        if not role:
            continue
        normalized = {
            "role": role,
            "content": _normalize_openai_content(msg.get("content")),
        }
        if msg.get("id") or msg.get("msgId"):
            normalized["msgId"] = msg.get("id") or msg.get("msgId")
        if msg.get("meta") or msg.get("metadata"):
            normalized["meta"] = msg.get("meta") or msg.get("metadata")
        raw_messages.append(normalized)

    # Attach legacy top-level images/files if present
    raw_messages = _attach_media(raw_messages, body)
    messages = [Message(**m) for m in raw_messages]

    header = Header(
        reqId=req_id,
        sessionId=session_id,
        parentMsgId=body.get("parent_message_id"),
        systemParams=SystemParams(userId=body.get("user") or "user"),
    )

    parameters = None
    if isinstance(body.get("parameters"), dict):
        try:
            parameters = Parameters(**body["parameters"])
        except Exception:
            parameters = None

    return ChatRequest(
        model=body.get("model"),
        parameters=parameters,
        header=header,
        body=Body(stream=stream, messages=messages),
    )


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """
    接收符合新协议的 ChatRequest 对象
    协议格式：
    {
      "model": "qwen3-max",
      "parameters": {...},
      "header": {
        "reqId": "...",
        "sessionId": "...",
        "parentMsgId": "...",
        "systemParams": {...}
      },
      "body": {
        "stream": true,
        "messages": [...]
      }
    }
    """
    # 先读取原始请求体用于调试
    try:
        body = await request.json()
        logger.info(f"Received request body: {body}")

        # 支持两种协议：直接的 ChatRequest，或 OpenAI 兼容格式
        if isinstance(body, dict) and body.get("header") and body.get("body"):
            chat_request = ChatRequest(**body)
        else:
            _log_request_summary(body if isinstance(body, dict) else {})
            chat_request = _build_chat_request_from_openai_payload(body)

        if not chat_request.body.messages:
            return JSONResponse({"error": "No messages provided"}, status_code=400)
    except Exception as e:
        logger.error(f"Failed to parse ChatRequest: {e}")
        logger.error(f"Request body was: {body}")
        return JSONResponse(
            {"error": f"Invalid request format: {str(e)}"},
            status_code=422
        )

    # 使用 MainChatRouter 创建事件流
    router = MainChatRouter(chat_request)
    event_stream = router.create_event_stream()

    def event_generator():
        for event in event_stream():
            # 后端日志观测每个 SSE chunk（长度截断）
            try:
                preview = event if isinstance(event, str) else str(event)
                if len(preview) > 500:
                    preview = preview[:500] + "...(truncated)"
                logger.info("[SSE] sending chunk: %s", preview)
            except Exception:
                logger.info("[SSE] sending chunk: <unserializable>")
            yield event

    return StreamingResponse(event_generator(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=config.API_SERVER_PORT, workers=1)
