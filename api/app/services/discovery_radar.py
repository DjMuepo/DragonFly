from __future__ import annotations
from typing import Dict, Any, List
import random

SAMPLE_OBJECTS = [
    {"type": "object", "label": "chair", "distance_km": 0.2},
    {"type": "object", "label": "tool", "distance_km": 0.6},
    {"type": "object", "label": "hook", "distance_km": 0.4},
]

SAMPLE_PRINTERS = [
    {"type": "printer", "name": "LA Maker Print Hub", "distance_km": 0.8},
    {"type": "printer", "name": "Pasadena Prototype Lab", "distance_km": 1.7},
]

SAMPLE_MISSIONS = [
    {"type": "mission", "name": "Scan a Chair"},
    {"type": "mission", "name": "Scan a Tool"},
]

SAMPLE_REPAIRS = [
    {"type": "repair", "label": "broken bracket"},
    {"type": "repair", "label": "cabinet hinge"},
]

def build_radar(payload: Dict[str, Any]) -> Dict[str, Any]:
    lat = payload.get("lat")
    lon = payload.get("lon")
    is_paid = bool(payload.get("is_paid", False))

    objects = random.sample(SAMPLE_OBJECTS, len(SAMPLE_OBJECTS))
    printers = random.sample(SAMPLE_PRINTERS, len(SAMPLE_PRINTERS))
    missions = random.sample(SAMPLE_MISSIONS, len(SAMPLE_MISSIONS))
    repairs = random.sample(SAMPLE_REPAIRS, len(SAMPLE_REPAIRS))

    radar_items: List[Dict[str, Any]] = []
    radar_items.extend(objects)
    radar_items.extend(printers)
    radar_items.extend(missions)
    radar_items.extend(repairs)

    return {
        "ok": True,
        "location": {"lat": lat, "lon": lon},
        "items": radar_items,
        "premium_features_unlocked": is_paid,
    }
