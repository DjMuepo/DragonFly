from __future__ import annotations
import json, os, time
from typing import Dict, Any, List

EVENTS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "events_v2.jsonl"))

def append_event(event: Dict[str, Any]) -> Dict[str, Any]:
    event = dict(event)
    event.setdefault("ts", int(time.time()))
    with open(EVENTS_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event

def read_events(limit: int = 1000) -> List[Dict[str, Any]]:
    if not os.path.exists(EVENTS_PATH):
        return []
    items: List[Dict[str, Any]] = []
    with open(EVENTS_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except Exception:
                continue
    return items[-limit:]
