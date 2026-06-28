from __future__ import annotations
from typing import Dict, Any
from app.services.live_detection import process_live_detection
from app.services.fix_object import generate_fix_plan

def route_camera_action(payload: Dict[str, Any]) -> Dict[str, Any]:
    detection = process_live_detection(payload)
    workflow = detection.get("workflow")

    if workflow == "fix_object":
        fix = generate_fix_plan({
            "label": detection.get("label"),
            "confidence": detection.get("confidence"),
            "user_notes": payload.get("user_notes") or "",
        })
        return {
            "ok": True,
            "route": "fix_object",
            "detection": detection,
            "fix_plan": fix,
        }

    if workflow == "scan_world":
        return {
            "ok": True,
            "route": "scan_world",
            "detection": detection,
            "scan_plan": {
                "message": detection.get("message"),
                "action": "open_scan_world",
                "premium_required": detection.get("premium_required", False),
                "suggested_actions": ["Replicate", "Design Similar", "Extract Part"],
            },
        }

    if workflow == "instant_builder":
        return {
            "ok": True,
            "route": "instant_builder",
            "detection": detection,
            "builder_plan": {
                "message": detection.get("message"),
                "template_family": detection.get("label"),
                "suggested_actions": ["Build Similar", "Resize", "Strengthen"],
            },
        }

    return {
        "ok": True,
        "route": "none",
        "detection": detection,
        "message": "No action suggested yet.",
    }
