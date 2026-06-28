from __future__ import annotations
from typing import Dict, Any
from app.services.prompt_engine import route_workflow

def process_live_detection(payload: Dict[str, Any]) -> Dict[str, Any]:
    label = (payload.get("label") or "").strip().lower()
    confidence = float(payload.get("confidence", 0) or 0)
    is_paid = bool(payload.get("is_paid", False))
    stable_frames = int(payload.get("stable_frames", 1) or 1)
    routed = route_workflow(label, confidence, is_paid=is_paid)
    routed["stable_frames"] = stable_frames
    routed["should_show_prompt"] = bool(routed["prompt"] and stable_frames >= 3)
    routed["debounce_ms"] = 5000 if routed["should_show_prompt"] else 0
    return routed
