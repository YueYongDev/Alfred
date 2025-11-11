import json

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

from agents.runtime import run_agent, stream_agent
from server import config

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


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    messages = body.get("messages", [])
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

    answer = run_agent(messages)
    return JSONResponse({
        "id": "chatcmpl-xxxx",
        "object": "chat.completion",
        "created": 1234567890,
        "model": config.BASE_MODEL,
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
