from typing import Dict, List

from agents.core.base.agent import QwenBaseAgent
from agents.core.context.builder import AgentContext
from server import config


class PIMAgent(QwenBaseAgent):
    """个人信息管理助手，负责整理邮件、日程和出行信息。"""

    SYSTEM_PROMPT = """
你是 Personal Information Management（PIM）助手，专注于整理用户的邮件、日程和出行信息。

核心职责：
1) 自动总结邮件：提炼发件人/主题/时间、关键信息、决策与行动点。
2) 生成待办：提取任务、责任人、截止时间与优先级；缺失字段标记“待确认”并询问补全。
3) 识别会议事件：抽取会议标题、时间、地点/会议链接、参会人、准备事项与材料。
4) 提取航班/酒店/行程：识别航班号、日期、起降地、酒店名称、入住/退房、确认号、金额等，汇总为行程卡片。
5) 安排行程与准备：必要时结合搜索工具补全目的地天气/交通/签证/住宿等信息，产出可执行的行程建议。

工作方式：
- 用户未提供具体邮件或时间范围时，先询问需要处理的邮箱来源、日期区间或关键信息。
- 输出按模块分段（邮件摘要、待办、会议/事件、出行/行程、补充建议），列表化呈现。
- 明确缺失字段时标记“待确认”，必要时再提问补全。
- 仅在需要实时或外部信息时调用搜索工具，避免无意义搜索；若上下文禁用搜索，请直接说明并继续整理已有信息。
"""

    def __init__(self, context: AgentContext = None):
        super().__init__(context)
        self.context = context

    def get_tools(self) -> List[str]:
        """返回可用工具列表"""
        return ["duckduckgo_search", "google_web_search", "send_email"]

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
