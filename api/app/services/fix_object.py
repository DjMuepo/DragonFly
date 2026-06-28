from __future__ import annotations
from typing import Dict, Any

SUPPORTED_BROKEN_PARTS = {
    "bracket": {
        "replacement_family": "bracket",
        "failure_region": "joint_interface",
        "recommended_material": "PETG",
        "base_confidence": 0.86,
    },
    "hinge": {
        "replacement_family": "bracket",
        "failure_region": "rotational_joint",
        "recommended_material": "PETG",
        "base_confidence": 0.82,
    },
    "clip": {
        "replacement_family": "clip",
        "failure_region": "snap_arm",
        "recommended_material": "PETG",
        "base_confidence": 0.84,
    },
    "handle": {
        "replacement_family": "support",
        "failure_region": "mount_point",
        "recommended_material": "ABS",
        "base_confidence": 0.79,
    },
    "hook": {
        "replacement_family": "hook",
        "failure_region": "load_bend",
        "recommended_material": "PETG",
        "base_confidence": 0.88,
    },
}

def generate_fix_plan(payload: Dict[str, Any]) -> Dict[str, Any]:
    label = (payload.get("label") or "").strip().lower()
    confidence = float(payload.get("confidence", 0) or 0)
    user_notes = payload.get("user_notes") or ""
    info = SUPPORTED_BROKEN_PARTS.get(label)
    if not info:
        return {
            "ok": False,
            "message": "Unsupported repair target",
            "suggested_next_step": "Try Scan the World or Instant Builder",
        }

    repair_confidence = round(min(0.97, (info["base_confidence"] + confidence) / 2), 3)
    object_dna = {
        "geometry": {
            "family": info["replacement_family"],
            "source_label": label,
        },
        "structure": {
            "failure_region": info["failure_region"],
            "repair_mode": "replacement",
            "auto_reinforce": True,
        },
        "print_profile": {
            "material": info["recommended_material"],
            "estimated_print_success": repair_confidence,
        },
        "ai_generation": {
            "source": "fix_this_object",
            "notes": user_notes,
        },
        "user_edits": [],
        "outcomes": {},
    }

    quick_actions = [
        "Generate replacement",
        "Strengthen automatically",
        "Resize fit",
        "Print nearby",
    ]

    return {
        "ok": True,
        "replacement_family": info["replacement_family"],
        "failure_region": info["failure_region"],
        "recommended_material": info["recommended_material"],
        "repair_confidence": repair_confidence,
        "object_dna": object_dna,
        "quick_actions": quick_actions,
        "message": f"This looks like a broken {label}. I can generate a printable replacement.",
    }
