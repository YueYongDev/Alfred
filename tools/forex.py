"""Foreign exchange rate tool using exchangerate-api.com."""

from __future__ import annotations

import os
from typing import Any, Dict

from qwen_agent.tools.base import register_tool
from tools.base import QwenAgentBaseTool
from tools.common import dump, safe_get_json

API_BASE = "https://v6.exchangerate-api.com/v6"
API_KEY = os.getenv("EXCHANGE_RATE_API_KEY")

@register_tool("fx_rate")
class ForexRateTool(QwenAgentBaseTool):
    description = "查询两种货币的实时汇率。"
    parameters = {
        "type": "object",
        "properties": {
            "base": {"type": "string", "description": "基准货币，默认 USD"},
            "quote": {"type": "string", "description": "目标货币，默认 CNY"},
        },
        "required": [],
    }

    def _execute_tool(self, params: Dict[str, Any], **_: Any) -> str:
        args = self._verify_json_format_args(params or {})
        base = (args.get("base") or "USD").upper()
        quote = (args.get("quote") or "CNY").upper()
        if not API_KEY:
            return dump({"task": "fx_rate", "status": "error", "error": "缺少 EXCHANGE_RATE_API_KEY"})
        status, payload = safe_get_json(f"{API_BASE}/{API_KEY}/latest/{base}")
        if status == "error":
            return dump({"task": "fx_rate", "status": status, "error": payload.get("error")})
        if payload.get("result") != "success":
            return dump(
                {
                    "task": "fx_rate",
                    "status": "error",
                    "error": payload.get("error-type") or payload.get("error") or "汇率接口返回失败",
                }
            )
        rate = (payload.get("conversion_rates") or {}).get(quote)
        if rate is None:
            return dump({"task": "fx_rate", "status": "error", "error": f"无法获取 {base}->{quote} 汇率"})
        return f"{base} -> {quote} 汇率: {rate}"
