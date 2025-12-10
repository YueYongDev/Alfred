import abc
import json
from typing import Optional

from qwen_agent.tools import BaseTool

from agents.core.context.builder import AgentContext
from server.app import logger


class QwenBaseTool(BaseTool, abc.ABC):
    """
    带有统一日志记录功能的工具抽象基类
    """

    def __init__(self, context: Optional[AgentContext] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.context = context or AgentContext()

    def call(self, params: str, **kwargs) -> str:
        """
        带有统一日志记录的调用方法
        子类需要实现 _execute 方法来处理具体的业务逻辑
        """
        tool_name = self.__class__.__name__
        logger.info(tool_name, "call", "start", params, "context", self.context)

        try:
            result = self._execute(params, **kwargs)
            logger.info(tool_name, "call", "success", result)
            return result
        except Exception as e:
            error_msg = f"Tool execution error: {str(e)}"
            logger.error(e, tool_name, "call", "execution_error")
            return json.dumps({"error": error_msg}, ensure_ascii=False)

    @abc.abstractmethod
    def _execute(self, params: str, **kwargs) -> str:
        """
        执行具体业务逻辑的抽象方法，子类必须实现
        """
        pass

    def format_arguments(self, arguments: str) -> str:
        """
        格式化工具调用的 arguments，用于在 UI 中展示

        默认实现：直接返回原始 arguments
        子类可以重写此方法来实现自定义格式化逻辑

        Args:
            arguments: 原始 arguments 字符串（通常是 JSON）

        Returns:
            str: 格式化后的 arguments 字符串
        """
        return arguments

    def format_result(self, result: str) -> str:
        """
        格式化工具执行结果，用于在 UI 中展示

        默认实现：直接返回原始结果
        子类可以重写此方法来实现自定义格式化逻辑

        Args:
            result: 原始结果字符串（通常是 JSON）

        Returns:
            str: 格式化后的结果字符串
        """
        return result
