"""Daily hot trend tool."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import requests
from qwen_agent.tools.base import register_tool
from tools.base import QwenAgentBaseTool

from server import config
from tools.common import HTTP_TIMEOUT, dump, normalize_base

DAILY_HOT_API_BASE = normalize_base(config.DAILY_HOT_API_BASE)


class DailyHotService:
    """Lightweight client for the DailyHot service."""

    def __init__(self, base_url: str = DAILY_HOT_API_BASE):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    def list_categories(self) -> Tuple[str, List[Dict[str, str]]]:
        status, data = self._get_json(f"{self.base_url}/all")
        if status == "error":
            return status, data
        if data.get("code") != 200:
            return "error", {"error": f"unexpected response code: {data.get('code')}"}
        return "ok", data.get("routes") or []

    def fetch_hot_list(self, path: str) -> Tuple[str, Dict[str, Any]]:
        normalized_path = path if path.startswith("/") else f"/{path}"
        status, data = self._get_json(f"{self.base_url}{normalized_path}")
        if status == "error":
            return status, data
        if data.get("code") != 200:
            return "error", {"error": f"unexpected response code: {data.get('code')}", "path": normalized_path}
        return "ok", data

    def _get_json(self, url: str) -> Tuple[str, Dict[str, Any]]:
        try:
            resp = self.session.get(url, timeout=HTTP_TIMEOUT)
            resp.raise_for_status()
            return "ok", resp.json()
        except requests.RequestException as exc:
            return "error", {"error": str(exc), "endpoint": url}


@register_tool("daily_hot_trends")
class DailyHotTrendsTool(QwenAgentBaseTool):
    description = "抓取 Daily Hot 服务的热点榜单，用于灵感/热点洞察。"
    parameters = {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "description": "可选，只获取指定榜单（支持名称或路径，例如 36kr 或 /36kr）。"
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

    def _execute_tool(self, params: Dict[str, Any], **_: Any) -> str:
        args = self._verify_json_format_args(params or {})
        category = (args.get("category") or "").strip()
        limit = _normalize_limit(args.get("limit", 5))
        service = DailyHotService()

        status, categories = service.list_categories()
        if status == "error":
            return dump({"task": "daily_hot", "status": "error", "error": categories.get("error")})

        if category:
            target = _match_category(categories, category)
            if not target:
                return dump({
                    "task": "daily_hot",
                    "status": "error",
                    "error": f"未找到匹配的榜单: {category}"
                })
            path = target.get("path")
            fetch_status, payload = service.fetch_hot_list(path or category)
            if fetch_status == "error":
                return dump({"task": "daily_hot", "status": "error", "error": payload.get("error")})
            return _format_hot_board(target.get("name") or category, payload, limit)

        boards: List[str] = [f"来源：{service.base_url}"]
        for cat in categories:
            name = cat.get("name") or cat.get("path")
            path = cat.get("path")
            if not path:
                continue
            fetch_status, payload = service.fetch_hot_list(path)
            if fetch_status == "error":
                boards.append(f"\n# {name or path}\n- 获取失败: {payload.get('error')}")
                continue
            boards.append(_format_hot_board(name or path, payload, limit))
        return "\n\n".join([b for b in boards if b.strip()])


def _normalize_limit(limit: Optional[int]) -> int:
    try:
        value = int(limit)
    except (TypeError, ValueError):
        value = 5
    return max(1, min(value, 20))


def _match_category(routes: List[Dict[str, Any]], category: str) -> Optional[Dict[str, Any]]:
    normalized = category.lower().lstrip("/")
    for cat in routes:
        name = (cat.get("name") or "").lower()
        path = (cat.get("path") or "").lower().lstrip("/")
        if normalized in (name, path):
            return cat
    return None


def _format_hot_board(category_name: str, payload: Dict[str, Any], limit: int) -> str:
    title = payload.get("title") or category_name
    board_type = payload.get("type")
    update_time = payload.get("updateTime") or payload.get("time")
    lines = [f"# {title}"]
    meta = []
    if board_type:
        meta.append(f"类型: {board_type}")
    if update_time:
        meta.append(f"更新时间: {update_time}")
    if meta:
        lines.append("；".join(meta))

    data = payload.get("data") or []
    if not data:
        lines.append("- 暂无数据")
        return "\n".join(lines)

    for idx, item in enumerate(data[:limit], 1):
        hot_score = item.get("hot")
        desc = item.get("desc") or item.get("description") or ""
        url = item.get("url") or ""
        headline = f"{idx}. {item.get('title', '')}"
        if hot_score not in (None, ""):
            headline += f" | 热度: {hot_score}"
        lines.append(headline)
        if desc:
            lines.append(f"   摘要: {desc}")
        if url:
            lines.append(f"   链接: {url}")
    return "\n".join(lines)
