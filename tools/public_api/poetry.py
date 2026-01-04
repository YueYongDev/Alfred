"""Poetry API (PoetryDB)."""

from __future__ import annotations

from typing import Any, Dict, List

from qwen_agent.tools.base import register_tool

from tools.core.base import QwenAgentBaseTool
from tools.core.utils import dump, safe_get_json

POETRY_BASE = "https://poetrydb.org"


def _normalize_limit(raw: Any, default: int = 5, max_value: int = 20) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = default
    return max(1, min(value, max_value))


@register_tool("poetry_search")
class PoetrySearchTool(QwenAgentBaseTool):
    description = "从 PoetryDB 搜索诗歌（按作者或标题）。"
    parameters = {
        "type": "object",
        "properties": {
            "author": {
                "type": "string",
                "description": "作者名（可选，author 与 title 至少一个）",
            },
            "title": {
                "type": "string",
                "description": "诗歌标题关键词（可选）",
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
        author = (args.get("author") or "").strip()
        title = (args.get("title") or "").strip()
        if not author and not title:
            return dump({"task": "poetry_search", "status": "error", "error": "需要 author 或 title"})

        limit = _normalize_limit(args.get("limit"))
        if author and title:
            endpoint = f"{POETRY_BASE}/author,title/{author};{title}"
        elif author:
            endpoint = f"{POETRY_BASE}/author/{author}"
        else:
            endpoint = f"{POETRY_BASE}/title/{title}"

        status, payload = safe_get_json(endpoint)
        if status == "error":
            return dump({"task": "poetry_search", "status": status, "error": payload.get("error")})

        items: List[Dict[str, Any]] = []
        for item in (payload or [])[:limit]:
            items.append(
                {
                    "title": item.get("title"),
                    "author": item.get("author"),
                    "lines": item.get("lines"),
                    "linecount": item.get("linecount"),
                }
            )

        return dump(
            {
                "task": "poetry_search",
                "status": "ok",
                "author": author or None,
                "title": title or None,
                "count": len(items),
                "results": items,
            }
        )
