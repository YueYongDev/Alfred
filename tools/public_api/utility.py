"""Utility public APIs: IPify and Bored."""

from __future__ import annotations

from typing import Any, Dict

from qwen_agent.tools.base import register_tool

from tools.core.base import QwenAgentBaseTool
from tools.core.utils import dump, safe_get_json

IPIFY_API = "https://api.ipify.org"
BORED_API = "https://www.boredapi.com/api/activity"


@register_tool("get_public_ip")
class PublicIPTool(QwenAgentBaseTool):
    description = "获取公网 IP（IPify）。"
    parameters = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    def _execute_tool(self, params: Dict[str, Any], **_: Any) -> str:
        _ = self._verify_json_format_args(params or {})
        status, payload = safe_get_json(f"{IPIFY_API}?format=json")
        if status == "error":
            return dump({"task": "get_public_ip", "status": status, "error": payload.get("error")})

        return dump({"task": "get_public_ip", "status": "ok", "ip": payload.get("ip")})


@register_tool("random_activity")
class RandomActivityTool(QwenAgentBaseTool):
    description = "随机推荐活动（Bored API）。"
    parameters = {
        "type": "object",
        "properties": {
            "type": {
                "type": "string",
                "description": "活动类型（可选），如 education、recreational、social、charity",
            },
            "participants": {
                "type": "integer",
                "description": "参与人数（可选）",
            },
        },
        "required": [],
    }

    def _execute_tool(self, params: Dict[str, Any], **_: Any) -> str:
        args = self._verify_json_format_args(params or {})
        activity_type = (args.get("type") or "").strip()
        participants = args.get("participants")

        query = []
        if activity_type:
            query.append(f"type={activity_type}")
        if participants:
            query.append(f"participants={participants}")

        url = BORED_API
        if query:
            url += "?" + "&".join(query)

        status, payload = safe_get_json(url)
        if status == "error":
            return dump({"task": "random_activity", "status": status, "error": payload.get("error")})

        if payload.get("error"):
            return dump({"task": "random_activity", "status": "error", "error": payload.get("error")})

        return dump(
            {
                "task": "random_activity",
                "status": "ok",
                "activity": payload.get("activity"),
                "type": payload.get("type"),
                "participants": payload.get("participants"),
                "price": payload.get("price"),
                "link": payload.get("link"),
            }
        )
