"""Science public APIs: arXiv and Launch Library 2."""

from __future__ import annotations

from typing import Any, Dict, List
import json
import xml.etree.ElementTree as ET

import requests
from qwen_agent.tools.base import register_tool

from tools.core.base import QwenAgentBaseTool
from tools.core.utils import dump, HTTP_TIMEOUT

ARXIV_API = "http://export.arxiv.org/api/query"
LL2_LAUNCH_API = "https://ll.thespacedevs.com/2.2.0/launch/"


def _normalize_limit(raw: Any, default: int = 5, max_value: int = 20) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = default
    return max(1, min(value, max_value))


def _safe_get_text(url: str) -> Dict[str, Any]:
    try:
        resp = requests.get(url, timeout=HTTP_TIMEOUT)
        resp.raise_for_status()
        return {"status": "ok", "text": resp.text}
    except requests.RequestException as exc:
        return {"status": "error", "error": str(exc)}


@register_tool("arxiv_search")
class ArxivSearchTool(QwenAgentBaseTool):
    description = "在 arXiv 中检索论文（Atom feed）。"
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "检索关键词（将匹配标题/摘要/作者）",
            },
            "max_results": {
                "type": "integer",
                "minimum": 1,
                "maximum": 20,
                "default": 5,
                "description": "返回结果条数，默认 5，最大 20",
            },
            "sort_by": {
                "type": "string",
                "enum": ["relevance", "lastUpdatedDate", "submittedDate"],
                "default": "relevance",
                "description": "排序字段",
            },
            "sort_order": {
                "type": "string",
                "enum": ["ascending", "descending"],
                "default": "descending",
                "description": "排序方向",
            },
        },
        "required": ["query"],
    }

    def _execute_tool(self, params: Dict[str, Any], **_: Any) -> str:
        args = self._verify_json_format_args(params)
        query = (args.get("query") or "").strip()
        if not query:
            return dump({"task": "arxiv_search", "status": "error", "error": "query 不能为空"})

        max_results = _normalize_limit(args.get("max_results"))
        sort_by = args.get("sort_by") or "relevance"
        sort_order = args.get("sort_order") or "descending"

        url = (
            f"{ARXIV_API}?search_query=all:{query}&start=0&max_results={max_results}"
            f"&sortBy={sort_by}&sortOrder={sort_order}"
        )

        result = _safe_get_text(url)
        if result.get("status") == "error":
            return dump({"task": "arxiv_search", "status": "error", "error": result.get("error")})

        try:
            root = ET.fromstring(result.get("text") or "")
        except ET.ParseError as exc:
            return dump({"task": "arxiv_search", "status": "error", "error": f"XML 解析失败: {exc}"})

        ns = {"atom": "http://www.w3.org/2005/Atom"}
        entries = root.findall("atom:entry", ns)
        items: List[Dict[str, Any]] = []
        for entry in entries[:max_results]:
            title = (entry.findtext("atom:title", default="", namespaces=ns) or "").strip()
            summary = (entry.findtext("atom:summary", default="", namespaces=ns) or "").strip()
            published = entry.findtext("atom:published", default="", namespaces=ns)
            updated = entry.findtext("atom:updated", default="", namespaces=ns)
            entry_id = entry.findtext("atom:id", default="", namespaces=ns)
            authors = [
                (author.findtext("atom:name", default="", namespaces=ns) or "").strip()
                for author in entry.findall("atom:author", ns)
            ]
            items.append(
                {
                    "title": title,
                    "summary": summary,
                    "published": published,
                    "updated": updated,
                    "id": entry_id,
                    "authors": authors,
                }
            )

        return dump(
            {
                "task": "arxiv_search",
                "status": "ok",
                "query": query,
                "count": len(items),
                "results": items,
            }
        )


@register_tool("launches")
class LaunchLibraryTool(QwenAgentBaseTool):
    description = "获取航天发射任务列表（Launch Library 2）。"
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "关键词过滤（可选）",
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

        url = f"{LL2_LAUNCH_API}?limit={limit}"
        if query:
            url += f"&search={query}"

        result = _safe_get_text(url)
        if result.get("status") == "error":
            return dump({"task": "launches", "status": "error", "error": result.get("error")})

        try:
            data = json.loads(result.get("text") or "")
        except ValueError as exc:
            return dump({"task": "launches", "status": "error", "error": f"JSON 解析失败: {exc}"})

        items: List[Dict[str, Any]] = []
        for item in (data.get("results") or [])[:limit]:
            mission = item.get("mission") or {}
            items.append(
                {
                    "name": item.get("name"),
                    "net": item.get("net"),
                    "status": (item.get("status") or {}).get("name"),
                    "launch_service_provider": (item.get("launch_service_provider") or {}).get("name"),
                    "mission_type": mission.get("type"),
                    "mission_description": mission.get("description"),
                    "pad": (item.get("pad") or {}).get("name"),
                    "location": ((item.get("pad") or {}).get("location") or {}).get("name"),
                    "url": item.get("url"),
                }
            )

        return dump(
            {
                "task": "launches",
                "status": "ok",
                "query": query or None,
                "count": len(items),
                "results": items,
            }
        )
