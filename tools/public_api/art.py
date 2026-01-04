"""Art public API: Art Institute of Chicago."""

from __future__ import annotations

from typing import Any, Dict, List

from qwen_agent.tools.base import register_tool

from tools.core.base import QwenAgentBaseTool
from tools.core.utils import dump, safe_get_json

AIC_SEARCH = "https://api.artic.edu/api/v1/artworks/search"


def _normalize_limit(raw: Any, default: int = 5, max_value: int = 20) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = default
    return max(1, min(value, max_value))


@register_tool("art_search")
class ArtSearchTool(QwenAgentBaseTool):
    description = "在芝加哥艺术学院（AIC）数据库中检索艺术品。"
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "检索关键词（作品名/作者/风格）",
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
            return dump({"task": "art_search", "status": "error", "error": "query 不能为空"})

        limit = _normalize_limit(args.get("limit"))
        status, payload = safe_get_json(
            f"{AIC_SEARCH}?q={query}&limit={limit}&fields=id,title,artist_title,date_display,image_id,api_link"
        )
        if status == "error":
            return dump({"task": "art_search", "status": status, "error": payload.get("error")})

        items: List[Dict[str, Any]] = []
        for item in (payload.get("data") or [])[:limit]:
            image_id = item.get("image_id")
            image_url = None
            if image_id:
                image_url = f"https://www.artic.edu/iiif/2/{image_id}/full/843,/0/default.jpg"
            items.append(
                {
                    "id": item.get("id"),
                    "title": item.get("title"),
                    "artist": item.get("artist_title"),
                    "date": item.get("date_display"),
                    "api_link": item.get("api_link"),
                    "image_url": image_url,
                }
            )

        return dump(
            {
                "task": "art_search",
                "status": "ok",
                "query": query,
                "count": len(items),
                "results": items,
            }
        )
