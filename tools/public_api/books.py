"""Books public APIs: Open Library and Gutendex."""

from __future__ import annotations

from typing import Any, Dict, List

from qwen_agent.tools.base import register_tool

from tools.core.base import QwenAgentBaseTool
from tools.core.utils import dump, safe_get_json

OPEN_LIBRARY_SEARCH = "https://openlibrary.org/search.json"
GUTENDEX_SEARCH = "https://gutendex.com/books"


def _normalize_limit(raw: Any, default: int = 5, max_value: int = 20) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = default
    return max(1, min(value, max_value))


@register_tool("book_search")
class BookSearchTool(QwenAgentBaseTool):
    description = "在 Open Library 中搜索图书与作者信息。"
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "检索关键词（书名/作者/主题）",
            },
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 20,
                "default": 5,
                "description": "返回结果条数，默认 5，最大 20",
            },
        },
        "required": ["query"],
    }

    def _execute_tool(self, params: Dict[str, Any], **_: Any) -> str:
        args = self._verify_json_format_args(params)
        query = (args.get("query") or "").strip()
        if not query:
            return dump({"task": "book_search", "status": "error", "error": "query 不能为空"})

        limit = _normalize_limit(args.get("limit"))
        status, payload = safe_get_json(f"{OPEN_LIBRARY_SEARCH}?q={query}&limit={limit}")
        if status == "error":
            return dump({"task": "book_search", "status": status, "error": payload.get("error")})

        docs = payload.get("docs") or []
        items: List[Dict[str, Any]] = []
        for item in docs[:limit]:
            items.append(
                {
                    "title": item.get("title"),
                    "author": (item.get("author_name") or [None])[0],
                    "first_publish_year": item.get("first_publish_year"),
                    "edition_count": item.get("edition_count"),
                    "key": item.get("key"),
                }
            )

        return dump(
            {
                "task": "book_search",
                "status": "ok",
                "query": query,
                "count": len(items),
                "results": items,
            }
        )


@register_tool("gutenberg_search")
class GutenbergSearchTool(QwenAgentBaseTool):
    description = "搜索古登堡公共领域书库（Gutendex）。"
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "检索关键词（书名/作者）",
            },
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 20,
                "default": 5,
                "description": "返回结果条数，默认 5，最大 20",
            },
        },
        "required": ["query"],
    }

    def _execute_tool(self, params: Dict[str, Any], **_: Any) -> str:
        args = self._verify_json_format_args(params)
        query = (args.get("query") or "").strip()
        if not query:
            return dump({"task": "gutenberg_search", "status": "error", "error": "query 不能为空"})

        limit = _normalize_limit(args.get("limit"))
        status, payload = safe_get_json(f"{GUTENDEX_SEARCH}?search={query}")
        if status == "error":
            return dump({"task": "gutenberg_search", "status": status, "error": payload.get("error")})

        items: List[Dict[str, Any]] = []
        for item in (payload.get("results") or [])[:limit]:
            authors = [author.get("name") for author in item.get("authors") or []]
            items.append(
                {
                    "title": item.get("title"),
                    "authors": authors,
                    "languages": item.get("languages"),
                    "download_count": item.get("download_count"),
                    "id": item.get("id"),
                }
            )

        return dump(
            {
                "task": "gutenberg_search",
                "status": "ok",
                "query": query,
                "count": len(items),
                "results": items,
            }
        )
