from __future__ import annotations
from typing import Dict, Any

SUPPORTED_FAMILIES = {
    "chair": {"workflow": "scan_world", "message": "This looks like a chair. Scan it?"},
    "desk": {"workflow": "scan_world", "message": "This looks like a desk. Scan for parts or design similar?"},
    "bracket": {"workflow": "fix_object", "message": "This looks like a bracket. Generate printable version?"},
    "hinge": {"workflow": "fix_object", "message": "This looks like a broken hinge-like part. Generate replacement?"},
    "hook": {"workflow": "scan_world", "message": "This looks like a hook. Scan it?"},
    "clip": {"workflow": "fix_object", "message": "This looks like a clip. Repair or regenerate it?"},
    "container": {"workflow": "instant_builder", "message": "This looks like a container. Build a similar version?"},
    "support": {"workflow": "instant_builder", "message": "This looks like a support part. Generate a printable version?"},
    "tool": {"workflow": "scan_world", "message": "This looks like a tool. Scan it?"},
}

def detect_actionability(label: str, confidence: float) -> Dict[str, Any]:
    label_n = (label or "").strip().lower()
    info = SUPPORTED_FAMILIES.get(label_n)
    if not info or confidence < 0.72:
        return {
            "prompt": False,
            "label": label_n,
            "confidence": confidence,
            "workflow": None,
            "message": "Point at an object to scan",
            "premium_required": False,
        }
    premium_required = info["workflow"] == "scan_world"
    return {
        "prompt": True,
        "label": label_n,
        "confidence": confidence,
        "workflow": info["workflow"],
        "message": info["message"],
        "premium_required": premium_required,
    }

def route_workflow(label: str, confidence: float, is_paid: bool = False) -> Dict[str, Any]:
    result = detect_actionability(label, confidence)
    if result["prompt"] and result["premium_required"] and not is_paid:
        result["workflow"] = "upsell_scan_world"
        result["message"] = result["message"] + " Unlock Scan the World to continue."
    return result
