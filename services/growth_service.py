"""Services for growth intelligence data sources (Daily Hot, etc.)."""

from __future__ import annotations

from typing import Dict, List, Optional

from client.daily_hot_client import DailyHotClient
from server import config


def fetch_daily_hot(category: Optional[str] = None, limit: int = 5) -> Dict:
    """Fetch trending topics from the external Daily Hot service."""
    client = DailyHotClient(base_url=config.DAILY_HOT_API_BASE)
    limit = max(1, min(limit, 20))

    if category:
        payload = _fetch_single_category(client, category, limit)
        results = {payload["category"]: payload["items"]}
    else:
        results = {}
        for cat in client.get_all_categories():
            name = cat.get("name")
            path = cat.get("path")
            if not name or not path:
                continue
            items = _safe_take(client.get_hot_list(path) or {}, limit)
            if items:
                results[name] = items

    return {
        "task": "daily_hot",
        "source": config.DAILY_HOT_API_BASE,
        "results": results,
    }


def _fetch_single_category(client: DailyHotClient, category: str, limit: int) -> Dict:
    target_path = _resolve_category_path(client, category)
    items = _safe_take(client.get_hot_list(target_path) or {}, limit)
    return {"category": category, "items": items}


def _resolve_category_path(client: DailyHotClient, category: str) -> str:
    normalized = category.lower()
    for cat in client.get_all_categories():
        name = (cat.get("name") or "").lower()
        if name == normalized:
            path = cat.get("path")
            if path:
                return path
    raise ValueError(f"Category '{category}' not found in Daily Hot service.")


def _safe_take(payload: Dict, limit: int) -> List[Dict]:
    items = []
    for item in (payload.get("data") or [])[:limit]:
        items.append({
            "title": item.get("title"),
            "description": item.get("desc"),
            "hot_score": item.get("hot"),
            "url": item.get("url"),
            "source": payload.get("title"),
        })
    return items
