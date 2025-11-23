from __future__ import annotations

from typing import Any, Dict, List

from duckduckgo_search import DDGS
from qwen_agent.tools.base import register_tool

from tools.base import QwenAgentBaseTool
from tools.common import dump


def _normalize_max_results(raw: Any) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return 5
    return max(1, min(value, 10))


@register_tool("duckduckgo_search")
class DuckDuckGoSearch(QwenAgentBaseTool):
    """DuckDuckGo search tool to avoid paid Google quota usage."""

    description = "使用 DuckDuckGo 搜索公开网页，返回标题、摘要与链接。"
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索关键词或问题。",
            },
            "max_results": {
                "type": "integer",
                "minimum": 1,
                "maximum": 10,
                "default": 5,
                "description": "返回结果条数，建议 1-10。",
            },
            "region": {
                "type": "string",
                "default": "wt-wt",
                "description": "地区/语言代码，默认全球(wt-wt)。例如 cn-zh 表示中文中国区。",
            },
        },
        "required": ["query"],
    }

    def _execute_tool(self, params: Dict[str, Any], **_: Any) -> str:
        args = self._verify_json_format_args(params or {})
        query = (args.get("query") or "").strip()
        if not query:
            return dump({"task": "duckduckgo_search", "status": "error", "error": "query 不能为空"})

        max_results = _normalize_max_results(args.get("max_results"))
        region = (args.get("region") or "wt-wt").strip() or "wt-wt"

        results: List[Dict[str, Any]] = []
        with DDGS() as ddgs:
            for item in ddgs.text(query, region=region, max_results=max_results):
                results.append(
                    {
                        "title": item.get("title"),
                        "snippet": item.get("body"),
                        "url": item.get("href"),
                        "source": item.get("source"),
                    }
                )
                if len(results) >= max_results:
                    break

        return dump(
            {
                "task": "duckduckgo_search",
                "status": "ok",
                "query": query,
                "region": region,
                "results": results,
            }
        )
