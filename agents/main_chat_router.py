import json
from typing import Any

from qwen_agent.agents import FnCallAgent

from agents.basic_chat_agent import BasicChatAgent
from agents.core.chat_request import ChatRequest
from agents.core.chat_response import ChatResponse
from agents.core.qwen_agent_context_builder import QwenAgentContextBuilder
from agents.core.qwen_agent_request_helper import convert_chat_request_to_messages
from agents.core.qwen_agent_router import QwenAgentRouter
# 修改导入，使用简化版的事件流处理器
from agents.core.stream.event_stream_handler import EventStreamHandler
from agents.image_agent import ImageAgent
from agents.planning_agent import PlanningAgent
from server.app import logger

class MainChatRouter:
    """主聊天代理类，负责创建和管理聊天流程"""

    def __init__(self, request: ChatRequest):
        """
        初始化主聊天代理

        Args:
            request: 聊天请求对象
        """
        self.request = request
        self.qa_messages = None
        self.bot = None

    def create_event_stream(self) -> Any:
        """
        创建主聊天代理的事件流

        Returns:
            事件流生成器
        """
        # OneLog.debug(f"Request: {self.request.model_dump_json()}")

        # 解析请求消息
        self.qa_messages = convert_chat_request_to_messages(self.request)
        logger.debug(f"QA Messages: {self.qa_messages}")

        # 创建智能助手
        self.bot = self._create_bot()

        # 创建简化版事件流处理器并返回其生成器
        handler = EventStreamHandler(self.request, self.bot, self.qa_messages)
        return handler.generate_stream

    def _create_bot(self) -> FnCallAgent:
        """
        创建主聊天代理机器人

        Returns:
            FnCallAgent实例
        """
        # 构建上下文
        ctx = QwenAgentContextBuilder.buildContext(self.request, self.qa_messages)

        # 基础对话助手（默认兜底Agent，放在第一位）
        bot_basic_chat = BasicChatAgent(ctx).create_agent()

        # 多模态Agent（图片理解、图片生成、图片修改）
        bot_image = ImageAgent(ctx).create_agent()

        # # 文档Agent（文档RAG、文档翻译）
        # bot_doc = DocAgent(ctx).create_agent()

        # 任务编排Agent（根据workflow编排子agent）
        bot_plan = PlanningAgent(bot_basic_chat, bot_image).create_agent()

        # 用qwen3-max做路由模型
        main_chat_router_llm_config = {'model': "qwen-plus-latest"}
        main_chat_router = QwenAgentRouter(
            llm=main_chat_router_llm_config,
            agents=[bot_basic_chat, bot_image],  # BasicChatAgent放在第一位作为默认兜底
            function_list=[],
        )
        return main_chat_router

    def get_non_stream_result(self) -> ChatResponse:
        """
        获取非流式结果，等待流式结果生成完毕后返回最后的结果

        Returns:
            ChatResponse: 最终的聊天响应结果
        """
        # OneLog.debug(f"Non-stream request: {self.request.model_dump_json()}")

        # 解析请求消息
        self.qa_messages = convert_chat_request_to_messages(self.request)
        # 创建智能助手
        self.bot = self._create_bot()

        # 创建简化版事件流处理器
        handler = EventStreamHandler(self.request, self.bot, self.qa_messages)

        # 遍历所有流式输出，收集最后的结果
        last_result = None
        try:
            for stream_data in handler.generate_stream():
                # 解析流式数据，寻找最后一个有效的响应
                if stream_data.startswith("data: "):
                    json_str = stream_data[6:].strip()  # 去掉 "data: " 前缀
                    if json_str:
                        try:
                            parsed_data = json.loads(json_str)
                            # 检查是否是有效的结果事件（content-generated 或 task-finished）
                            if parsed_data.get("header").get("event") in ["content-generated", "task-finished"]:
                                last_result = parsed_data
                        except json.JSONDecodeError:
                            continue

        except Exception as e:
            logger.error(e, f"Non-stream error, task_id: {self.request.communication.reqid}, error: {str(e)}")
            return ChatResponse.from_failed_content(
                code=500,
                message=f"Non-stream processing error: {str(e)}",
                task_id=self.request.communication.reqid
            )

        # 如果没有找到有效结果，返回默认错误响应
        if last_result is None:
            return ChatResponse.from_failed_content(
                code=500,
                message="No valid result found in stream",
                task_id=self.request.communication.reqid
            )

        # 将最后的结果转换为 ChatResponse 对象
        try:
            # 使用 model_validate 方法进行正确的数据转换，包括嵌套对象
            response = ChatResponse.model_validate(last_result)
            return response
        except Exception as e:
            logger.error(e,
                         f"Failed to parse final result, task_id: {self.request.communication.reqid}, error: {str(e)}")
            return ChatResponse.from_failed_content(
                code=500,
                message=f"Failed to parse final result: {str(e)}",
                task_id=self.request.communication.reqid
            )