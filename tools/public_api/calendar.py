"""Calendar public APIs: holidays and namedays."""

from __future__ import annotations

from typing import Any, Dict

from qwen_agent.tools.base import register_tool

from tools.core.base import QwenAgentBaseTool
from tools.core.utils import dump, safe_get_json

NAGER_BASE = "https://date.nager.at/api/v3"
NAMEDAY_BASE = "https://nameday.abalin.net/api/V1"


@register_tool("public_holidays")
class PublicHolidaysTool(QwenAgentBaseTool):
    description = "查询指定国家/年份的公共节假日列表（Nager.Date）。"
    parameters = {
        "type": "object",
        "properties": {
            "country_code": {
                "type": "string",
                "description": "国家代码（ISO 3166-1 alpha-2），如 CN、US、JP",
            },
            "year": {
                "type": "integer",
                "description": "年份，如 2024",
            },
        },
        "required": ["country_code", "year"],
    }

    def _execute_tool(self, params: Dict[str, Any], **_: Any) -> str:
        args = self._verify_json_format_args(params)
        country_code = (args.get("country_code") or "").upper()
        year = args.get("year")
        if not country_code or not year:
            return dump({"task": "public_holidays", "status": "error", "error": "缺少 country_code 或 year"})

        status, payload = safe_get_json(f"{NAGER_BASE}/PublicHolidays/{year}/{country_code}")
        if status == "error":
            return dump({"task": "public_holidays", "status": status, "error": payload.get("error")})

        items = []
        for item in payload or []:
            items.append(
                {
                    "date": item.get("date"),
                    "local_name": item.get("localName"),
                    "name": item.get("name"),
                    "type": item.get("type"),
                    "country": item.get("countryCode"),
                }
            )

        return dump(
            {
                "task": "public_holidays",
                "status": "ok",
                "country_code": country_code,
                "year": year,
                "count": len(items),
                "holidays": items,
            }
        )


@register_tool("nameday_lookup")
class NamedayLookupTool(QwenAgentBaseTool):
    description = "查询指定日期的姓名节（Namedays Calendar）。"
    parameters = {
        "type": "object",
        "properties": {
            "country_code": {
                "type": "string",
                "description": "国家代码（如 US、SE、PL），可选，默认 US",
            },
            "month": {
                "type": "integer",
                "description": "月份 (1-12)",
            },
            "day": {
                "type": "integer",
                "description": "日期 (1-31)",
            },
        },
        "required": ["month", "day"],
    }

    def _execute_tool(self, params: Dict[str, Any], **_: Any) -> str:
        args = self._verify_json_format_args(params)
        country_code = (args.get("country_code") or "US").upper()
        month = args.get("month")
        day = args.get("day")
        if not month or not day:
            return dump({"task": "nameday_lookup", "status": "error", "error": "缺少 month 或 day"})

        status, payload = safe_get_json(f"{NAMEDAY_BASE}/getdate?country={country_code}&month={month}&day={day}")
        if status == "error":
            return dump({"task": "nameday_lookup", "status": status, "error": payload.get("error")})

        return dump(
            {
                "task": "nameday_lookup",
                "status": "ok",
                "country_code": country_code,
                "month": month,
                "day": day,
                "namedays": (payload.get("data") or {}).get("namedays"),
            }
        )
