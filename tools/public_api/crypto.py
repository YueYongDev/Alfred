"""Cryptocurrency public APIs: CoinCap and Coinpaprika."""

from __future__ import annotations

from typing import Any, Dict, List

from qwen_agent.tools.base import register_tool

from tools.core.base import QwenAgentBaseTool
from tools.core.utils import dump, safe_get_json

COINCAP_ASSET = "https://api.coincap.io/v2/assets"
COINPAPRIKA_TICKER = "https://api.coinpaprika.com/v1/tickers"


def _normalize_limit(raw: Any, default: int = 5, max_value: int = 20) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = default
    return max(1, min(value, max_value))


@register_tool("crypto_price")
class CryptoPriceTool(QwenAgentBaseTool):
    description = "查询加密货币价格（CoinCap）。"
    parameters = {
        "type": "object",
        "properties": {
            "symbol": {
                "type": "string",
                "description": "币种符号，如 BTC、ETH",
            },
        },
        "required": ["symbol"],
    }

    def _execute_tool(self, params: Dict[str, Any], **_: Any) -> str:
        args = self._verify_json_format_args(params)
        symbol = (args.get("symbol") or "").strip().upper()
        if not symbol:
            return dump({"task": "crypto_price", "status": "error", "error": "symbol 不能为空"})

        status, payload = safe_get_json(f"{COINCAP_ASSET}?search={symbol}")
        if status == "error":
            return dump({"task": "crypto_price", "status": status, "error": payload.get("error")})

        data = payload.get("data") or []
        match = None
        for item in data:
            if (item.get("symbol") or "").upper() == symbol:
                match = item
                break
        if not match:
            match = data[0] if data else None
        if not match:
            return dump({"task": "crypto_price", "status": "error", "error": f"未找到币种 {symbol}"})

        return dump(
            {
                "task": "crypto_price",
                "status": "ok",
                "symbol": match.get("symbol"),
                "name": match.get("name"),
                "price_usd": match.get("priceUsd"),
                "change_24h": match.get("changePercent24Hr"),
                "market_cap": match.get("marketCapUsd"),
                "rank": match.get("rank"),
            }
        )


@register_tool("crypto_market")
class CryptoMarketTool(QwenAgentBaseTool):
    description = "获取加密货币市场概览（Coinpaprika）。"
    parameters = {
        "type": "object",
        "properties": {
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
        limit = _normalize_limit(args.get("limit"))
        status, payload = safe_get_json(COINPAPRIKA_TICKER)
        if status == "error":
            return dump({"task": "crypto_market", "status": status, "error": payload.get("error")})

        items: List[Dict[str, Any]] = []
        for item in (payload or [])[:limit]:
            quotes = item.get("quotes") or {}
            usd = quotes.get("USD") or {}
            items.append(
                {
                    "id": item.get("id"),
                    "symbol": item.get("symbol"),
                    "name": item.get("name"),
                    "rank": item.get("rank"),
                    "price_usd": usd.get("price"),
                    "volume_24h": usd.get("volume_24h"),
                    "market_cap": usd.get("market_cap"),
                }
            )

        return dump(
            {
                "task": "crypto_market",
                "status": "ok",
                "count": len(items),
                "results": items,
            }
        )
