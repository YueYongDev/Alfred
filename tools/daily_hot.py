"""Daily hot trend tool."""

from __future__ import annotations

from typing import Any, Dict, Optional

from qwen_agent.tools.base import register_tool, BaseTool

from server import config
from tools.common import dump, normalize_base, safe_get_json, HTTP_TIMEOUT

DAILY_HOT_API_BASE = normalize_base(config.DAILY_HOT_API_BASE)


@register_tool("daily_hot_trends")
class DailyHotTrendsTool(BaseTool):
    description = "抓取 Daily Hot 服务的热点榜单，用于灵感/热点洞察。"
    parameters = {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "description": "可选，只获取指定榜单（按照名称匹配）。"
            },
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 20,
                "default": 5,
                "description": "每个榜单返回的条数。"
            }
        },
        "required": [],
    }

    def call(self, params: Dict[str, Any], **_: Any) -> str:
        args = self._verify_json_format_args(params or {})
        result = _fetch_daily_hot(args.get("category"), args.get("limit", 5))
        if result.get("status") == "error":
            return dump(result)

        formatted = [f"来源：{result['source']}"]
        for category, items in result.get("results", {}).items():
            formatted.append(f"\n# {category}")
            for item in items:
                formatted.append(
                    f"- {item.get('title')} (score={item.get('hot_score')})\n  {item.get('description') or ''}\n  {item.get('url') or ''}"
                )
        return "\n".join(formatted)


def _fetch_daily_hot(category: Optional[str], limit: int) -> Dict:
    limit = max(1, min(limit or 5, 20))
    status, categories = safe_get_json(f"{DAILY_HOT_API_BASE}/all")
    if status == "error":
        return {"task": "daily_hot", "endpoint": f"{DAILY_HOT_API_BASE}/all", "status": status,
                "error": categories.get("error")}

    routes = categories.get("routes") or []
    if category:
        target_path = _resolve_category_path(routes, category)
        if not target_path:
            return {"task": "daily_hot", "status": "error", "error": f"Category '{category}' not found"}
        items = _safe_take(safe_get_json(
            f"{DAILY_HOT_API_BASE}{_ensure_leading_slash(target_path)}", HTTP_TIMEOUT)[1], limit)
        results = {category: items}
    else:
        results = {}
        for cat in routes:
            name = cat.get("name")
            path = cat.get("path")
            if not name or not path:
                continue
            _, payload = safe_get_json(
                f"{DAILY_HOT_API_BASE}{_ensure_leading_slash(path)}")
            items = _safe_take(payload, limit)
            if items:
                results[name] = items

    return {"task": "daily_hot", "source": DAILY_HOT_API_BASE, "status": "ok", "results": results}


def _resolve_category_path(routes: list, category: str) -> Optional[str]:
    normalized = category.lower()
    for cat in routes:
        name = (cat.get("name") or "").lower()
        if name == normalized:
            return cat.get("path")
    return None


def _safe_take(payload: Dict, limit: int) -> list:
    items = []
    for item in (payload.get("data") or [])[:limit]:
        items.append({
            "title": item.get("title"),
            "description": item.get("desc"),
            "hot_score": item.get("hot"),
            "url": item.get("url"),
            "source": payload.get("title"),
        })
    return items


def _ensure_leading_slash(path: str) -> str:
    return path if path.startswith("/") else f"/{path}"
