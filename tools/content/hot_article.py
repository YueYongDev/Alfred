"""Fetch article details (summary/tags) for a given URL."""

from __future__ import annotations

from typing import Any, Dict

from qwen_agent.tools.base import register_tool
from tools.core.base import QwenAgentBaseTool

from server import config
from tools.core.utils import dump, normalize_base, safe_post_json

SUMMARY_API = normalize_base(config.WEB_SUMMARY_API)


def website_summary(url: str) -> Dict[str, Any]:
    """Call the summary service to analyze a single URL."""
    if not url:
        return {"task": "daily_hot_article", "status": "error", "error": "URL 不能为空"}

    status, payload = safe_post_json(f"{SUMMARY_API}", {"url": url}, timeout=60)
    if status == "error":
        return {"task": "daily_hot_article", "status": "error", "error": payload.get("error")}

    return {
        "task": "daily_hot_article",
        "status": "ok",
        "summary": payload.get("summary", ""),
        "tags": payload.get("tags") or [],
    }


@register_tool("web_summary")
class WebSummaryTool(QwenAgentBaseTool):
    description = "根据链接获取文章内容并且生成摘要和标签"
    parameters = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "需要分析的文章链接，必须是可访问的完整 URL。"
            }
        },
        "required": ["url"],
    }

    def _execute_tool(self, params: Dict[str, Any], **_: Any) -> str:
        args = self._verify_json_format_args(params or {})
        url = (args.get("url") or "").strip()
        if not url:
            return dump({"task": "daily_hot_article", "status": "error", "error": "URL 不能为空"})

        result = website_summary(url)
        if result.get("status") == "error":
            return dump(result)

        tags = result.get("tags") or []
        summary = result.get("summary") or ""
        output = [f"URL: {url}"]
        if summary:
            output.append(f"摘要: {summary}")
        if tags:
            output.append(f"标签: {', '.join(tags)}")
        return "\n".join(output)
