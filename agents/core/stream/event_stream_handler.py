import json
import logging
from typing import Generator, Any, List, Dict

from fastapi.encoders import jsonable_encoder
from qwen_agent.agents import FnCallAgent

from agents.core.messaging import ChatRequest

logger = logging.getLogger(__name__)


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
        生成 SSE 事件流 - 将 bot.run 的结果转换为 SSE 格式
        """
        logger.debug(f"Starting SSE stream generation, task_id: {self.task_id}")

        try:
            result = self.bot.run(messages=self.qa_messages)
            if result is None:
                logger.debug(f"Agent returned None result, task_id: {self.task_id}")
                yield "data: {}\n\n"
                return

            # 遍历 bot.run 的结果并转换为 OpenAI SSE 格式
            for chunk in result:
                # 如果 chunk 是字符串，认为是增量文本内容
                if isinstance(chunk, str):
                    # 转换为 OpenAI 格式
                    openai_chunk = {
                        "choices": [{
                            "delta": {
                                "content": chunk
                            },
                            "index": 0
                        }]
                    }
                    json_str = json.dumps(openai_chunk, ensure_ascii=False)
                    yield f"data: {json_str}\n\n"
                # 如果 chunk 是字典且包含 content 字段
                elif isinstance(chunk, dict):
                    # 检查是否为工具调用或工具结果
                    if 'function_call' in chunk or chunk.get('role') == 'function':
                        # 发送完整的工具调用或结果对象
                        json_str = json.dumps(chunk, ensure_ascii=False)
                        yield f"data: {json_str}\n\n"
                    else:
                        content = chunk.get("content", "")
                        if content:
                            openai_chunk = {
                                "choices": [{
                                    "delta": {
                                        "content": content
                                    },
                                    "index": 0
                                }]
                            }
                            json_str = json.dumps(openai_chunk, ensure_ascii=False)
                            yield f"data: {json_str}\n\n"
                # 其他类型尝试提取文本内容
                else:
                    try:
                        # 尝试从对象中提取 content 或转为字符串
                        content = getattr(chunk, 'content', str(chunk))
                        if content:
                            openai_chunk = {
                                "choices": [{
                                    "delta": {
                                        "content": content
                                    },
                                    "index": 0
                                }]
                            }
                            json_str = json.dumps(openai_chunk, ensure_ascii=False)
                            yield f"data: {json_str}\n\n"
                    except Exception as e:
                        logger.warning(f"Failed to process chunk type: {type(chunk)}, task_id: {self.task_id}, error: {e}")

            # 正常结束，发送 DONE 标记
            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"Error in stream generation, task_id: {self.task_id}, error: {str(e)}")
            # 直接输出错误信息
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"
            # 错误结束，也发送 DONE 标记
            yield "data: [DONE]\n\n"

        logger.debug(f"SSE stream generation completed, task_id: {self.task_id}")
