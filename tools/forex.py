"""Foreign exchange rate tool using exchangerate.host."""

from __future__ import annotations

from typing import Any, Dict

from qwen_agent.tools import BaseTool

from tools.common import dump, safe_get_json

API_BASE = "https://api.exchangerate.host/latest"

class ForexRateTool(BaseTool):
    name = "fx_rate"
    description = "查询两种货币的实时汇率（使用 exchangerate.host 公开接口）。"
    parameters = {
        "type": "object",
        "properties": {
            "base": {"type": "string", "description": "基准货币，默认 USD"},
            "quote": {"type": "string", "description": "目标货币，默认 CNY"},
        },
        "required": [],
    }

    def call(self, params: Dict[str, Any], **_: Any) -> str:
        args = self._verify_json_format_args(params or {})
        base = (args.get("base") or "USD").upper()
        quote = (args.get("quote") or "CNY").upper()
        status, payload = safe_get_json(f"{API_BASE}?base={base}&symbols={quote}")
        if status == "error":
            return dump({"task": "fx_rate", "status": status, "error": payload.get("error")})
        rate = (payload.get("rates") or {}).get(quote)
        if rate is None:
            return dump({"task": "fx_rate", "status": "error", "error": f"无法获取 {base}->{quote} 汇率"})
        return f"{base} -> {quote} 汇率: {rate}"
