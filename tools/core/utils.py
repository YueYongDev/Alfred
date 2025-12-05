from __future__ import annotations

import json
from typing import Dict, Tuple

import requests

HTTP_TIMEOUT = 30


def normalize_base(url: str) -> str:
    if url.startswith("http://") or url.startswith("https://"):
        return url.rstrip("/")
    return f"http://{url.rstrip('/')}"


def safe_get_json(url: str, timeout: int = HTTP_TIMEOUT) -> Tuple[str, Dict]:
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        return "ok", resp.json()
    except requests.RequestException as exc:
        return "error", {"error": str(exc)}


def safe_post_json(url: str, payload: Dict, timeout: int = HTTP_TIMEOUT) -> Tuple[str, Dict]:
    try:
        resp = requests.post(url, json=payload, timeout=timeout)
        resp.raise_for_status()
        return "ok", resp.json()
    except requests.RequestException as exc:
        return "error", {"error": str(exc)}


def dump(obj: Dict) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)
