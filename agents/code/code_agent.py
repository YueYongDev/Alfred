from typing import List, Dict, Any

from qwen_agent.agents import FnCallAgent

from agents.core.base.agent import QwenBaseAgent
from agents.core.context.builder import AgentContext
from agents.core.tools.selector import convert_tool_names_to_instances
from server import config


class CodeAgent(QwenBaseAgent):
    """代码助手类，专注于帮助用户进行代码分析、执行和问题解决"""

    SYSTEM_PROMPT = '''
你是代码助手，专注代码分析、生成、调试与执行。
优先给出可运行的方案与简洁解释，遵循最佳实践并注意安全。
需要验证结果时使用代码执行工具并返回输出。
'''

    def __init__(self, context: AgentContext = None):
        """
        初始化代码助手

        Args:
            context: Agent上下文对象
        """
        super().__init__(context)
        self.context = context

    def get_tools(self) -> List[str]:
        """获取工具列表"""
        return ["code_interpreter", "python_executor"]

    def get_name(self) -> str:
        """获取Agent名称"""
        return '代码助手'

    def get_description(self) -> str:
        """获取Agent描述"""
        return (
            '专门处理所有代码相关任务，包括：1) 代码执行和运行；2) 代码分析和审查；'
            '3) 代码生成和优化；4) 编程问题解决。能够帮助用户进行Python编程、数据分析、'
            '算法实现、调试等各种编程相关活动。'
        )

    def get_llm_config(self) -> Dict[str, Any]:
        """获取LLM配置"""
        generate_cfg = {
            "temperature": 0.1  # 代码相关任务使用较低的温度以确保准确性
        }

        return {
            "model": config.LLM_CODE_MODEL,
            "model_type": config.LLM_PROVIDER,
            "model_server": config.LLM_BASE_URL,
            "api_key": config.LLM_API_KEY,
            "generate_cfg": generate_cfg
        }

    def create_agent(self) -> FnCallAgent:
        """
        创建并返回FnCallAgent实例

        Returns:
            FnCallAgent: 配置好的代码助手实例
        """
        return FnCallAgent(
            system_message=self.SYSTEM_PROMPT,
            llm=self.get_llm_config(),
            function_list=convert_tool_names_to_instances(self.get_tools(), self.context),
            name=self.get_name(),
            description=self.get_description()
        )
