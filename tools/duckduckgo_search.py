from __future__ import annotations

from typing import Any, Dict, List, Optional

from ddgs import DDGS
from ddgs.ddgs import DDGSException, TimeoutException
from qwen_agent.tools.base import register_tool

from tools.base import QwenAgentBaseTool
from tools.common import dump


def _normalize_max_results(raw: Any) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return 5
    return max(1, min(value, 10))


def _normalize_backend(raw: Any) -> str:
    value = (raw or "auto").strip().lower()
    return value or "auto"


def _format_result(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "title": item.get("title"),
        "snippet": item.get("body") or item.get("description"),
        "url": item.get("href") or item.get("url") or item.get("link"),
        "source": item.get("source") or item.get("provider") or item.get("engine"),
    }


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
            "backend": {
                "type": "string",
                "default": "auto",
                "description": "搜索后端，默认为 auto，可选 duckduckgo/bing/brave/yahoo/yandex/mojeek/wikipedia。",
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
        backend = _normalize_backend(args.get("backend"))

        results, backend_used, err = self._search_with_fallback(query, region, max_results, backend)
        if err:
            return dump(
                {
                    "task": "duckduckgo_search",
                    "status": "error",
                    "error": err,
                    "query": query,
                    "region": region,
                    "backend": backend_used or backend,
                }
            )

        return dump(
            {
                "task": "duckduckgo_search",
                "status": "ok",
                "query": query,
                "region": region,
                "backend": backend_used or backend,
                "results": results,
            }
        )

    def _search_with_fallback(
        self, query: str, region: str, max_results: int, backend: str
    ) -> tuple[List[Dict[str, Any]], Optional[str], Optional[str]]:
        # Try requested backend first, then auto aggregation as fallback
        backends = [backend]
        if "auto" not in backends:
            backends.append("auto")

        last_error: Optional[str] = None
        for be in backends:
            try:
                with DDGS() as ddgs:
                    raw_results = ddgs.text(
                        query,
                        region=region,
                        max_results=max_results,
                        backend=be,
                    )
                return [_format_result(item) for item in raw_results], be, None
            except (DDGSException, TimeoutException) as exc:
                last_error = f"ddgs error ({be}): {exc}"
            except Exception as exc:  # noqa: BLE001
                last_error = f"ddgs unexpected error ({be}): {exc}"
        return [], None, last_error or "ddgs search failed"
