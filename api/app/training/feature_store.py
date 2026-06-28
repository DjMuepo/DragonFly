from __future__ import annotations
import json, os, time
from typing import Dict, Any

FEATURES_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "feature_store.json"))

def load_features() -> Dict[str, Any]:
    if not os.path.exists(FEATURES_PATH):
        save_features({"updated_at": int(time.time()), "families": {}, "global": {}})
    with open(FEATURES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_features(data: Dict[str, Any]) -> None:
    with open(FEATURES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
