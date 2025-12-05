import json
from abc import ABC, abstractmethod
from typing import Dict, Any, List

from qwen_agent.agents import FnCallAgent

from agents.core.context.builder import AgentContext
from agents.core.tools.selector import convert_tool_names_to_instances
from server.app import logger


class QwenBaseAgent(ABC):
    """Qwen Agent基类，提供统一的日志记录和通用逻辑"""

    # 子类需要定义的属性
    SYSTEM_PROMPT: str = ""

    def __init__(self, context: AgentContext = None):
        """
        初始化Agent基类
        
        Args:
            context: Agent上下文对象
        """
        self.context = context
        self.tools = self.get_tools()
        self.name = self.get_name()
        self.description = self.get_description()

        # 记录初始化日志
        # OneLog.info(f"Initializing {self.__class__.__name__}: {self.name}")
        # OneLog.debug(f"{self.__class__.__name__} tools: {self.tools}")

    @abstractmethod
    def get_tools(self) -> List[str]:
        """获取工具列表，子类必须实现"""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """获取Agent名称，子类必须实现"""
        pass

    @abstractmethod
    def get_description(self) -> str:
        """获取Agent描述，子类必须实现"""
        pass

    def get_system_prompt(self) -> str:
        """
        获取系统提示词，子类可以重写此方法来实现动态系统提示词逻辑

        Returns:
            系统提示词字符串
        """
        return self.SYSTEM_PROMPT

    def get_llm_config(self) -> Dict[str, Any]:
        """
        获取LLM配置，子类可以重写以提供自定义配置
        
        Returns:
            LLM配置字典
        """
        # 默认返回简单配置，子类可以重写
        return {'model': 'qwen3-max'}

    def create_agent(self) -> FnCallAgent:
        """
        创建并返回FnCallAgent实例
        
        Returns:
            FnCallAgent: 配置好的Agent实例
        """
        llm_config = self.get_llm_config()

        # 记录创建日志
        logger.info(f"Creating {self.__class__.__name__} agent")
        logger.debug(f"{self.__class__.__name__} LLM Config: {json.dumps(llm_config, ensure_ascii=False)}")
        logger.debug(f"{self.__class__.__name__} System Prompt: {self.SYSTEM_PROMPT[:100]}...")
        logger.debug(
            f"{self.__class__.__name__} Context: {json.dumps(self.context.model_dump() if self.context else {}, ensure_ascii=False)}")

        # 使用动态系统提示词
        system_prompt = self.get_system_prompt()

        agent = FnCallAgent(
            system_message=system_prompt,
            llm=llm_config,
            function_list=convert_tool_names_to_instances(self.tools, self.context),
            name=self.name,
            description=self.description
        )

        logger.info(f"{self.__class__.__name__} agent created successfully")
        return agent

    def log_tool_call(self, tool_name: str, **kwargs):
        """
        记录工具调用日志
        
        Args:
            tool_name: 工具名称
            **kwargs: 工具调用参数
        """
        logger.info(f"{self.__class__.__name__} calling tool: {tool_name}")
        logger.debug(f"Tool call parameters: {json.dumps(kwargs, ensure_ascii=False)}")

    def log_agent_response(self, response: Any):
        """
        记录Agent响应日志
        
        Args:
            response: Agent响应内容
        """
        logger.info(f"{self.__class__.__name__} response generated")
        logger.debug(f"Response length: {len(str(response)) if response else 0}")
