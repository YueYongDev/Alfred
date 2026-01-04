import json
import logging
import uuid
from pathlib import Path
from typing import Any, Dict, List, Tuple

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from agents.core.messaging.chat_request import ChatRequest
# 添加必要的导入
from agents.routers.agent_router import AgentRouter
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
        if isinstance(tool, str):
            return {
                "name": tool,
                "description": "",
                "parameters": {},
                "agent": agent_name,
            }
        if isinstance(tool, dict):
            return {
                "name": tool.get("name", "tool"),
                "description": (tool.get("description") or "").strip(),
                "parameters": tool.get("parameters", {}) or {},
                "agent": tool.get("agent", agent_name),
            }

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
    from agents.core.messaging.chat_request import ChatRequest
    import uuid

    temp_request = ChatRequest(
        req_id=str(uuid.uuid4()),
        session_id=f"metadata_{uuid.uuid4()}",
        messages=[],
    )

    router = AgentRouter(temp_request)
    # 创建bot实例
    router.bot = router._create_bot()

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

def _find_latest_user(messages: List[Dict[str, Any]]) -> Tuple[int, Dict[str, Any] | None]:
    for idx in range(len(messages) - 1, -1, -1):
        msg = messages[idx]
        if isinstance(msg, dict) and msg.get("role") == "user":
            return idx, msg
    return -1, None


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


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """
    接收 ChatRequest 对象（精简版）
    {
      "model": "qwen3-max",
      "stream": true,
      "messages": [...],
      "req_id": "...",
      "session_id": "...",
      "user_id": "..."
    }
    """
    # 先读取原始请求体用于调试
    try:
        body = await request.json()
        logger.info(f"Received request body: {body}")

        _log_request_summary(body if isinstance(body, dict) else {})
        chat_request = ChatRequest(**body)

        if not chat_request.messages:
            return JSONResponse({"error": "No messages provided"}, status_code=400)
    except Exception as e:
        logger.error(f"Failed to parse ChatRequest: {e}")
        logger.error(f"Request body was: {body}")
        return JSONResponse(
            {"error": f"Invalid request format: {str(e)}"},
            status_code=422
        )

    # 使用 AgentRouter 创建事件流
    router = AgentRouter(chat_request)
    event_stream = router.create_event_stream()

    def event_generator():
        for event in event_stream():
            # 后端日志观测每个 SSE chunk（长度截断）
            try:
                preview = event if isinstance(event, str) else str(event)
                # logger.info("[SSE] sending chunk: %s", preview)
            except Exception:
                logger.info("[SSE] sending chunk: <unserializable>")
            yield event

    return StreamingResponse(event_generator(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=config.API_SERVER_PORT, workers=1)
