from typing import Dict, List

from agents.core.base.agent import QwenBaseAgent
from agents.core.context.builder import AgentContext
from server import config


class PublicAPIAgent(QwenBaseAgent):
    """公共 API 助手，整合免费公共接口工具。"""

    SYSTEM_PROMPT = """
你是公共 API 助手，擅长使用各类免费公开 API 提供结构化数据。
优先选择合适工具获取数据并进行简洁总结；必要时追问参数（如国家代码、关键词等）。
输出以“结果 + 要点”的形式，避免冗余。
"""

    def __init__(self, context: AgentContext = None):
        super().__init__(context)
        self.context = context

    def get_tools(self) -> List[str]:
        return [
            "public_holidays",
            "nameday_lookup",
            "book_search",
            "gutenberg_search",
            "poetry_search",
            "spaceflight_news",
            "crypto_price",
            "crypto_market",
            "arxiv_search",
            "launches",
            "art_search",
            "get_public_ip",
            "random_activity",
        ]

    def get_name(self) -> str:
        return "公共API助手"

    def get_description(self) -> str:
        return (
            "整合公共免费 API 的工具型助手，提供节假日、图书、诗歌、新闻、加密行情、"
            "论文、航天发射、艺术品、IP 查询与随机活动等信息。"
        )

    def get_llm_config(self) -> Dict[str, object]:
        return {
            "model": config.LLM_MODEL,
            "model_type": config.LLM_PROVIDER,
            "model_server": config.LLM_BASE_URL,
            "api_key": config.LLM_API_KEY,
            "generate_cfg": {"temperature": 0.3},
        }
