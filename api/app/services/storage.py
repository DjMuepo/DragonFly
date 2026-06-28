from __future__ import annotations
import json, os, time, uuid
from typing import Dict, Any

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data_store.json"))

def _seed() -> Dict[str, Any]:
    return {"users": [], "designs": [], "sessions": []}

def load_db() -> Dict[str, Any]:
    if not os.path.exists(DB_PATH):
        db = _seed()
        save_db(db)
        return db
    with open(DB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(db: Dict[str, Any]) -> None:
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"

def now_ts() -> int:
    return int(time.time())
