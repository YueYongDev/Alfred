import json
import logging
import time
import uuid
from typing import Any, Dict, Generator, List, Optional

from fastapi.encoders import jsonable_encoder
from qwen_agent.agents import FnCallAgent

from agents.core.messaging import ChatRequest

logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s %(name)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)


class EventStreamHandler:
    """
    将 Agent 输出转换为 OpenAI 风格的 SSE 流
    """

    def __init__(self, request: ChatRequest, bot: FnCallAgent, qa_messages: List[Dict[str, Any]]):
        self.request = request
        self.bot = bot
        self.qa_messages = qa_messages
        self.task_id = request.header.reqId if request.header else str(uuid.uuid4())
        self.model_name = request.model or "unknown-model"
        self._created_ts = int(time.time())
        self._full_content: str = ""
        self._role_sent = False
        self._tool_calls: Dict[str, Dict[str, str]] = {}
        self._tool_call_order: List[str] = []

    def _build_openai_chunk(self, delta: Dict[str, Any], finish_reason: Optional[str] = None) -> str:
        payload = {
            "id": self.task_id,
            "object": "chat.completion.chunk",
            "created": self._created_ts,
            "model": self.model_name,
            "choices": [
                {
                    "index": 0,
                    "delta": delta,
                    "finish_reason": finish_reason,
                }
            ],
        }
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    def _compose_delta(
        self,
        content: Optional[str] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        delta: Dict[str, Any] = {}
        if not self._role_sent:
            delta["role"] = "assistant"
            self._role_sent = True
        if content:
            delta["content"] = content
        if tool_calls:
            delta["tool_calls"] = tool_calls
        return delta

    @staticmethod
    def _normalize_message(msg: Any) -> Dict[str, Any]:
        if isinstance(msg, dict):
            return msg
        try:
            return jsonable_encoder(msg)
        except Exception:
            return {"role": "assistant", "content": str(msg)}

    @staticmethod
    def _flatten_text(content: Any) -> str:
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: List[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("text"):
                    parts.append(item.get("text", ""))
                elif isinstance(item, str):
                    parts.append(item)
            return "".join(parts)
        return str(content)

    def _content_delta(self, new_text: str) -> str:
        if not new_text:
            return ""
        if new_text.startswith(self._full_content):
            delta = new_text[len(self._full_content):]
        else:
            delta = new_text
        self._full_content = new_text
        return delta

    def _handle_tool_call(self, msg: Dict[str, Any]) -> List[str]:
        fc = msg.get("function_call") or {}
        if not isinstance(fc, dict):
            return []

        extra = msg.get("extra") or {}
        tool_id = extra.get("function_id") or msg.get("id") or f"call_{len(self._tool_call_order)}"

        include_name = tool_id not in self._tool_call_order
        if include_name:
            self._tool_call_order.append(tool_id)

        state = self._tool_calls.get(tool_id, {"name": "", "arguments": ""})
        name = fc.get("name") or state["name"]
        arguments = fc.get("arguments") or ""

        name_delta = name[len(state["name"]):] if name.startswith(state["name"]) else name
        args_delta = arguments[len(state["arguments"]):] if arguments.startswith(state["arguments"]) else arguments

        state["name"] = name
        state["arguments"] = arguments
        self._tool_calls[tool_id] = state

        tool_delta: Dict[str, Any] = {
            "index": self._tool_call_order.index(tool_id),
            "id": tool_id,
            "type": "function",
            "function": {},
        }
        if include_name or name_delta:
            tool_delta["function"]["name"] = name_delta or name
        if args_delta:
            tool_delta["function"]["arguments"] = args_delta

        if not tool_delta["function"]:
            return []

        delta = self._compose_delta(tool_calls=[tool_delta])
        return [self._build_openai_chunk(delta)]

    def _convert_chunk_to_openai(self, chunk: Any) -> List[str]:
        normalized: List[Dict[str, Any]] = []
        if isinstance(chunk, list):
            normalized = [self._normalize_message(m) for m in chunk if m is not None]
        elif chunk is not None:
            normalized = [self._normalize_message(chunk)]

        out: List[str] = []
        for msg in normalized:
            role = msg.get("role")
            if role == "assistant":
                out.extend(self._handle_tool_call(msg))
                text_delta = self._content_delta(self._flatten_text(msg.get("content")))
                if text_delta:
                    out.append(self._build_openai_chunk(self._compose_delta(content=text_delta)))
            # 工具执行结果不再单独下发给前端，避免破坏 OpenAI 协议
        return out

    def generate_stream(self) -> Generator[str, None, None]:
        """
        生成 SSE 事件流（OpenAI 兼容）
        """
        logger.info(f"Starting SSE stream generation, task_id: {self.task_id}")

        try:
            result = self.bot.run(messages=self.qa_messages)
            if result is None:
                logger.info(f"Agent returned None result, task_id: {self.task_id}")
                yield self._build_openai_chunk(self._compose_delta(), finish_reason="stop")
                yield "data: [DONE]\n\n"
                return

            for chunk in result:
                try:
                    preview = chunk if isinstance(chunk, str) else jsonable_encoder(chunk)
                    preview_str = json.dumps(preview, ensure_ascii=False) if not isinstance(preview, str) else preview
                except Exception:
                    preview_str = "<unserializable>"
                logger.info("[raw-chunk] type=%s task_id=%s payload=%s", type(chunk), self.task_id, preview_str[:500])

                try:
                    for piece in self._convert_chunk_to_openai(chunk):
                        yield piece
                except Exception as e:
                    logger.warning(f"Failed to emit chunk: type={type(chunk)}, task_id={self.task_id}, error={e}")

            yield self._build_openai_chunk(self._compose_delta(), finish_reason="stop")
            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"Error in stream generation, task_id: {self.task_id}, error: {str(e)}")
            error_delta = self._compose_delta(content=f"[error] {str(e)}")
            yield self._build_openai_chunk(error_delta, finish_reason="stop")
            yield "data: [DONE]\n\n"

        logger.info(f"SSE stream generation completed, task_id: {self.task_id}")
