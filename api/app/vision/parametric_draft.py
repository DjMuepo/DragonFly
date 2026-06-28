from __future__ import annotations
from typing import Dict, Any
from .family_priors import family_to_prior

def build_parametric_draft(*, family: str, bbox: Dict[str, Any], aspect_ratio: float, depth_ratio: float, depth_meta: Dict[str, Any]) -> Dict[str, Any]:
    prior = family_to_prior(family)
    width = 1.0
    height = max(0.35, min(1.8, 1.0 / max(0.5, aspect_ratio)))
    depth = max(0.15, min(1.2, (depth_ratio + prior["depth_bias"]) * 1.4))
    params: Dict[str, Any] = {
        "shape": prior["base_shape"],
        "prior": prior["prior"],
        "width": round(width, 3),
        "height": round(height, 3),
        "depth": round(depth, 3),
        "editable": prior["editable"],
    }
    f = family.lower()
    if f == "bracket":
        params.update({"mount_holes": 2, "thickness": 1.0, "arm_ratio": round(min(1.3, max(0.45, aspect_ratio)), 3)})
    elif f == "hook":
        params.update({"curve": 0.65, "thickness": 0.95, "mount_holes": 2})
    elif f == "clip":
        params.update({"jaw_gap": 0.22, "thickness": 0.92, "springiness": 0.6})
    elif f == "handle":
        params.update({"grip_thickness": 1.05, "length": round(max(0.8, height * 1.3), 3), "comfort": 0.7})
    elif f == "enclosure":
        params.update({"wall_thickness": 0.12, "lid": True, "mounts": 4})
    elif f == "adapter":
        params.update({"inner_diameter": 0.35, "outer_diameter": 0.55, "length": round(max(0.6, depth * 1.2), 3)})
    return {"family": family, "bbox": bbox, "aspect_ratio": round(aspect_ratio, 3), "estimated_depth_ratio": round(depth_ratio, 3), "depth_meta": depth_meta, "params": params, "confidence": 0.58 if family.lower() in ["bracket","hook","clip","handle","enclosure","adapter"] else 0.44, "notes": ["Family-aware parametric draft.", "Optimized for beginner editing.", "Best with clear side/profile photos."]}
