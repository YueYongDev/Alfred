import json
import logging
from typing import Any, Dict, List, Tuple

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

from agents.main_chat_agent import stream_agent, run_main_chat
from server import config

logger = logging.getLogger("server.app")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

app = FastAPI()


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
        logger.debug("raw files payload: %s", files)
        logger.debug("raw images payload: %s", images)


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    # _log_request_summary(body)

    messages = _attach_media(body.get("messages", []), body)
    stream = body.get("stream", False)

    # 提取用户最新提问（role=user）
    question = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            question = msg.get("content", "")
            break

    if not question:
        return JSONResponse({"error": "No user message found"}, status_code=400)

    if stream:
        def event_generator():
            for delta in stream_agent(messages):
                if not delta:
                    continue
                yield format_openai_stream_delta(delta)
            yield "data: [DONE]\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    answer = run_main_chat(messages)
    return JSONResponse({
        "id": "chatcmpl-xxxx",
        "object": "chat.completion",
        "created": 1234567890,
        "model": config.LLM_MODEL,
        "choices": [
            {
                "message": {"role": "assistant", "content": answer},
                "finish_reason": "stop",
                "index": 0,
            }
        ],
    })


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=config.API_SERVER_PORT, workers=1)
