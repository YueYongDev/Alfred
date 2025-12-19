from typing import Dict, List

from agents.core.base.agent import QwenBaseAgent
from agents.core.context.builder import AgentContext
from server import config


class PIMAgent(QwenBaseAgent):
    """个人信息管理助手，负责整理邮件、日程和出行信息。"""

    SYSTEM_PROMPT = """
你是 PIM 助手，整理邮件、日程和出行信息。
输出结构化模块：邮件摘要、待办、会议/事件、行程、补充建议。
缺失字段标记“待确认”，必要时追问；仅在需要实时外部信息时使用搜索工具。
"""

    def __init__(self, context: AgentContext = None):
        super().__init__(context)
        self.context = context

    def get_tools(self) -> List[str]:
        """返回可用工具列表"""
        return ["duckduckgo_search", "send_email"]

    def get_name(self) -> str:
        return "个人信息管理助手"

    def get_description(self) -> str:
        return (
            "整理邮件、日程、会议与出行信息，输出结构化摘要和待办，并在需要时使用搜索补全行程与准备信息。"
        )

    def get_llm_config(self) -> Dict[str, object]:
        generate_cfg = {
            "temperature": 0.3,
        }

        return {
            "model": config.LLM_MODEL,
            "model_type": config.LLM_PROVIDER,
            "model_server": config.LLM_BASE_URL,
            "api_key": config.LLM_API_KEY,
            "generate_cfg": generate_cfg
        }
