import logging
import json
import time
import uuid
from typing import Any, Dict, Generator, List

from qwen_agent.agents import FnCallAgent

from agents.core.messaging import ChatRequest
from fastapi.encoders import jsonable_encoder

logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s %(name)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)


class EventStreamHandler:
    """
    将 Agent 输出转换为 Qwen-Agent 原始协议的 SSE 流
    """

    def __init__(self, request: ChatRequest, bot: FnCallAgent, qa_messages: List[Dict[str, Any]]):
        self.request = request
        self.bot = bot
        self.qa_messages = qa_messages
        self.task_id = request.req_id or str(uuid.uuid4())
        self.model_name = request.model or "unknown-model"
        self._created_ts = int(time.time())

    def generate_stream(self) -> Generator[str, None, None]:
        """
        生成 SSE 事件流（Qwen-Agent 原始协议）
        """
        logger.info(f"Starting SSE stream generation, task_id: {self.task_id}")

        try:
            roles_preview = [
                m.get("role")
                for m in self.qa_messages
                if isinstance(m, dict)
            ]
            logger.info("[stream-input] task_id=%s roles=%s", self.task_id, roles_preview)
            result = self.bot.run(messages=self.qa_messages)
            if result is None:
                logger.info(f"Agent returned None result, task_id: {self.task_id}")
                yield "data: [DONE]\n\n"
                return

            for chunk in result:
                try:
                    payload = jsonable_encoder(chunk)
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                except Exception as e:
                    logger.warning(f"Failed to emit chunk: type={type(chunk)}, task_id={self.task_id}, error={e}")

            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"Error in stream generation, task_id: {self.task_id}, error: {str(e)}")
            error_payload = {"error": str(e)}
            yield f"data: {json.dumps(error_payload, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

        logger.info(f"SSE stream generation completed, task_id: {self.task_id}")
