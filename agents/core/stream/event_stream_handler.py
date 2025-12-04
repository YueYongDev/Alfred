import json
import logging
from typing import Any, Dict, List, Generator
from qwen_agent.agents import FnCallAgent

from agents.core.chat_request import ChatRequest

logger = logging.getLogger(__name__)

class EventStreamHandler:
    """简化版事件流处理器，直接流式输出数据到前端"""

    def __init__(self, request: ChatRequest, bot: FnCallAgent, qa_messages: List[Dict[str, Any]]):
        """
        初始化简化版事件流处理器

        Args:
            request: 聊天请求对象
            bot: 代理机器人
            qa_messages: QA消息列表
        """
        self.request = request
        self.bot = bot
        self.qa_messages = qa_messages
        self.task_id = request.communication.reqid

    def generate_stream(self) -> Generator[str, None, None]:
        """
        生成简化版的事件流

        Yields:
            事件流数据
        """
        try:
            # 发送任务开始事件
            yield self._yield_task_started()
            
            # 运行代理并流式输出结果
            for response in self.bot.run(self.qa_messages):
                # 直接将响应转换为JSON并发送
                if response:
                    # 如果响应是字典或对象，转换为JSON
                    if isinstance(response, dict):
                        content = response.get("content", "")
                    elif hasattr(response, "content"):
                        content = response.content
                    else:
                        content = str(response)
                    
                    # 发送内容到前端
                    if content:
                        yield self._yield_content(content)
            
            # 发送任务完成事件
            yield self._yield_task_finished()
            
        except Exception as e:
            logger.error(f"Error in stream generation, task_id: {self.task_id}, error: {str(e)}")
            yield self._yield_error(str(e))

    def _yield_task_started(self) -> str:
        """
        发送任务开始事件

        Returns:
            任务开始事件数据
        """
        data = {
            "header": {
                "event": "task-started",
                "taskId": self.task_id
            },
            "data": {
                "message": "Task started"
            }
        }
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

    def _yield_content(self, content: str) -> str:
        """
        发送内容事件

        Args:
            content: 要发送的内容

        Returns:
            内容事件数据
        """
        data = {
            "header": {
                "event": "content-generated",
                "taskId": self.task_id
            },
            "data": {
                "content": content
            }
        }
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

    def _yield_task_finished(self) -> str:
        """
        发送任务完成事件

        Returns:
            任务完成事件数据
        """
        data = {
            "header": {
                "event": "task-finished",
                "taskId": self.task_id
            },
            "data": {
                "message": "Task finished"
            }
        }
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

    def _yield_error(self, error_message: str) -> str:
        """
        发送错误事件

        Args:
            error_message: 错误消息

        Returns:
            错误事件数据
        """
        data = {
            "header": {
                "event": "error",
                "taskId": self.task_id
            },
            "data": {
                "message": f"处理过程中出现错误: {error_message}"
            }
        }
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"