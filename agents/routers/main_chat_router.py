import logging
from typing import Any

from qwen_agent.agents import FnCallAgent

from agents.chat.basic_chat_agent import BasicChatAgent
from agents.core.context.builder import QwenAgentContextBuilder
from agents.core.messaging.chat_request import ChatRequest
from agents.core.messaging.request_helper import convert_chat_request_to_messages
from agents.core.routing.router import QwenAgentRouter
# 修改导入，使用简化版的事件流处理器
from agents.core.stream.event_stream_handler import EventStreamHandler
from agents.multimodal.image_agent import ImageAgent
from agents.pim.pim_agent import PIMAgent
from agents.planning.planning_agent import PlanningAgent
from server import config

logger = logging.getLogger(__name__)

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
        logger.info(f"QA Messages: {self.qa_messages}")

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

        # 个人信息管理Agent（邮件、日程、出行）
        bot_pim = PIMAgent(ctx).create_agent()

        # 任务编排Agent（根据workflow编排子agent）
        bot_plan = PlanningAgent(bot_basic_chat, bot_image, bot_pim).create_agent()

        # 用qwen3-max做路由模型
        main_chat_router_llm_config = {
            "model": config.LLM_ROUTE_MODEL,
            "model_type": config.LLM_PROVIDER,
            "model_server": config.LLM_BASE_URL,
            "api_key": config.LLM_API_KEY,
        }
        main_chat_router = QwenAgentRouter(
            llm=main_chat_router_llm_config,
            agents=[bot_basic_chat, bot_image, bot_pim, bot_plan],  # BasicChatAgent放在第一位作为默认兜底
            function_list=[],
        )
        return main_chat_router
