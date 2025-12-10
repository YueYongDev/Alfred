import json
import logging
from typing import Generator, Any, List, Dict

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
    事件流处理器，负责处理与 Agent 的交互并生成 SSE 流
    """

    def __init__(self, request: ChatRequest, bot: FnCallAgent, qa_messages: List[Dict[str, Any]]):
        """
        初始化事件流处理器
        :param request: 聊天请求
        :param bot: Agent 实例
        :param qa_messages: 问答消息列表
        """
        self.request = request
        self.bot = bot
        self.qa_messages = qa_messages
        # 从新的协议中获取 task_id 和 model_name
        self.task_id = request.header.reqId if request.header else None
        self.model_name = request.model

    def generate_stream(self) -> Generator[str, None, None]:
        """
        生成 SSE 事件流 - 使用 qwen-agent 原生输出协议
        """
        logger.info(f"Starting SSE stream generation, task_id: {self.task_id}")

        try:
            result = self.bot.run(messages=self.qa_messages)
            if result is None:
                logger.info(f"Agent returned None result, task_id: {self.task_id}")
                yield "data: {}\n\n"
                return

            # 遍历 bot.run 的结果并转换为 OpenAI SSE 格式
            for chunk in result:
                # 主动打印原始 chunk，便于排查
                try:
                    preview = chunk if isinstance(chunk, str) else jsonable_encoder(chunk)
                    preview_str = json.dumps(preview, ensure_ascii=False) if not isinstance(preview, str) else preview
                except Exception:
                    preview_str = "<unserializable>"
                logger.info("[raw-chunk] type=%s task_id=%s payload=%s", type(chunk), self.task_id, preview_str[:500])

                # 直接透传 qwen-agent chunk，不做协议转换
                try:
                    if isinstance(chunk, (dict, list)):
                        json_str = json.dumps(chunk, ensure_ascii=False)
                    else:
                        json_str = str(chunk)
                    yield f"data: {json_str}\n\n"
                except Exception as e:
                    logger.warning(f"Failed to emit chunk: type={type(chunk)}, task_id={self.task_id}, error={e}")

            # 正常结束，发送 DONE 标记
            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"Error in stream generation, task_id: {self.task_id}, error: {str(e)}")
            # 直接输出错误信息
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"
            # 错误结束，也发送 DONE 标记
            yield "data: [DONE]\n\n"

        logger.info(f"SSE stream generation completed, task_id: {self.task_id}")
