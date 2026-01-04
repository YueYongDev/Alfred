"""News public API: Spaceflight News."""

from __future__ import annotations

from typing import Any, Dict, List

from qwen_agent.tools.base import register_tool

from tools.core.base import QwenAgentBaseTool
from tools.core.utils import dump, safe_get_json

SPACEFLIGHT_API = "https://api.spaceflightnewsapi.net/v4/articles"


def _normalize_limit(raw: Any, default: int = 5, max_value: int = 20) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = default
    return max(1, min(value, max_value))


@register_tool("spaceflight_news")
class SpaceflightNewsTool(QwenAgentBaseTool):
    description = "获取航天新闻（Spaceflight News）。"
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "关键词（可选）",
            },
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 20,
                "default": 5,
                "description": "返回结果条数，默认 5，最大 20",
            },
        },
        "required": [],
    }

    def _execute_tool(self, params: Dict[str, Any], **_: Any) -> str:
        args = self._verify_json_format_args(params or {})
        query = (args.get("query") or "").strip()
        limit = _normalize_limit(args.get("limit"))

        url = f"{SPACEFLIGHT_API}?limit={limit}"
        if query:
            url += f"&search={query}"

        status, payload = safe_get_json(url)
        if status == "error":
            return dump({"task": "spaceflight_news", "status": status, "error": payload.get("error")})

        items: List[Dict[str, Any]] = []
        for item in (payload.get("results") or [])[:limit]:
            items.append(
                {
                    "title": item.get("title"),
                    "summary": item.get("summary"),
                    "url": item.get("url"),
                    "published_at": item.get("published_at"),
                    "news_site": item.get("news_site"),
                }
            )

        return dump(
            {
                "task": "spaceflight_news",
                "status": "ok",
                "query": query or None,
                "count": len(items),
                "results": items,
            }
        )
