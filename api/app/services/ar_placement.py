from __future__ import annotations
from typing import Dict, Any

SUPPORTED_SURFACES = ["desk", "wall", "floor", "shelf"]

def generate_ar_placement_plan(payload: Dict[str, Any]) -> Dict[str, Any]:
    design_title = payload.get("design_title") or "Untitled Design"
    family = (payload.get("family") or "object").strip().lower()
    surface = (payload.get("surface") or "desk").strip().lower()
    width = float(payload.get("width_mm", 100) or 100)
    height = float(payload.get("height_mm", 100) or 100)
    depth = float(payload.get("depth_mm", 100) or 100)

    if surface not in SUPPORTED_SURFACES:
        surface = "desk"

    placement_mode = "horizontal_anchor" if surface in ("desk", "floor", "shelf") else "vertical_anchor"

    fit_checks = []
    if width > 300:
        fit_checks.append("Check width clearance before printing")
    if height > 250:
        fit_checks.append("Check vertical clearance")
    if family in ("hook", "bracket") and surface == "wall":
        fit_checks.append("Confirm wall mount alignment")
    if family in ("container", "support") and surface == "desk":
        fit_checks.append("Check desk footprint and stability")

    object_dna = {
        "geometry": {
            "family": family,
            "dimensions_mm": {"width": width, "height": height, "depth": depth},
        },
        "structure": {
            "placement_surface": surface,
            "placement_mode": placement_mode,
        },
        "ai_generation": {
            "source": "ar_object_placement",
        },
        "user_edits": [],
        "outcomes": {},
    }

    return {
        "ok": True,
        "design_title": design_title,
        "surface": surface,
        "placement_mode": placement_mode,
        "object_dna": object_dna,
        "fit_checks": fit_checks,
        "instructions": [
            "Place the object in the scene",
            "Adjust size and angle",
            "Check fit and clearance",
            "Continue to print when satisfied",
        ],
        "ar_preview": {
            "anchor_type": placement_mode,
            "show_bounding_box": True,
            "show_shadow": True,
            "allow_rotation": True,
            "allow_scaling": True,
        },
    }
