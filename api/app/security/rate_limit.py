from __future__ import annotations
import json, os, time
from typing import Dict

RATE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "rate_limits.json"))

def _load() -> Dict[str, dict]:
    if not os.path.exists(RATE_PATH):
        return {}
    try:
        with open(RATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save(data: Dict[str, dict]) -> None:
    with open(RATE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def check_and_increment(key: str, limit: int = 10, window_seconds: int = 900) -> Dict[str, object]:
    now = int(time.time())
    data = _load()
    item = data.get(key) or {"count": 0, "reset_at": now + window_seconds}
    if now >= int(item.get("reset_at", 0)):
        item = {"count": 0, "reset_at": now + window_seconds}
    blocked = int(item["count"]) >= limit
    if not blocked:
        item["count"] = int(item["count"]) + 1
        data[key] = item
        _save(data)
    return {"allowed": not blocked, "remaining": max(0, limit - int(item["count"])), "reset_at": item["reset_at"]}
