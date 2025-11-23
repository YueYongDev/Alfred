from qwen_agent.agents import Assistant
from qwen_agent.tools import WebSearch

from server import config
from tools.duckduckgo_search import DuckDuckGoSearch
from tools.google_web_search import GoogleWebSearch

WEB_SEARCH_PROMPT = (
    "你是网络搜索 Agent，擅长使用多种搜索引擎（如 Google、DuckDuckGo）"
    "快速检索并汇总最新的公开信息，优先调用 DuckDuckGo 以降低费用。"
    "最终回答时只输出总结，不要把工具调用的原始 JSON 或日志返回给用户。"
)


def web_search_assistant() -> Assistant:
    llm_cfg = {
        "model": config.LLM_MODEL,
        "model_server": config.LLM_BASE_URL,
        "api_key": config.LLM_API_KEY,
        "generate_cfg": {
            "temperature": config.LLM_TEMPERATURE,
        },
    }

    tool_instances = [
        DuckDuckGoSearch(),
        GoogleWebSearch(),
    ]

    return Assistant(
        function_list=tool_instances,
        llm=llm_cfg,
        system_message=WEB_SEARCH_PROMPT,
        name="web_search_agent",
        description="通用网络搜索助手，支持 DuckDuckGo 与 Google 搜索。",
    )
