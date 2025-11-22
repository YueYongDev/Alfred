"""Time utilities."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo

from qwen_agent.tools import BaseTool
from qwen_agent.tools.base import register_tool

DEFAULT_TZ = "Asia/Shanghai"

@register_tool("current_time")
class CurrentTimeTool(BaseTool):
    description = "获取当前时间，支持指定时区，返回 ISO8601 与格式化时间。"
    parameters = {
        "type": "object",
        "properties": {
            "timezone": {
                "type": "string",
                "description": "时区名称，例：Asia/Shanghai, UTC, America/Los_Angeles"
            }
        },
        "required": [],
    }

    def call(self, params: Dict[str, Any], **_: Any) -> str:
        args = self._verify_json_format_args(params or {})
        tz_name = args.get("timezone") or DEFAULT_TZ
        now_iso, now_human = _now_in_tz(tz_name)
        return f"Timezone: {tz_name}\nISO: {now_iso}\nLocal: {now_human}"


def _now_in_tz(tz_name: str) -> (str, str):
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo(DEFAULT_TZ)
        tz_name = DEFAULT_TZ
    now = datetime.now(tz)
    return now.isoformat(), now.strftime("%Y-%m-%d %H:%M:%S %Z")
