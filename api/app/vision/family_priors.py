from __future__ import annotations
from typing import Dict, Any

CORE_FAMILIES = ["bracket", "hook", "clip", "handle", "enclosure", "adapter"]

def family_to_prior(family: str) -> Dict[str, Any]:
    f = (family or "object").lower()
    if f == "bracket":
        return {"prior": "l_bracket", "base_shape": "box", "depth_bias": 0.22, "editable": ["thickness", "height", "mount_holes"]}
    if f == "hook":
        return {"prior": "hook_curve", "base_shape": "box", "depth_bias": 0.18, "editable": ["thickness", "curve", "mount_holes"]}
    if f == "clip":
        return {"prior": "clip_jaw", "base_shape": "wedge", "depth_bias": 0.16, "editable": ["jaw_gap", "thickness", "springiness"]}
    if f == "handle":
        return {"prior": "ergonomic_handle", "base_shape": "capsule", "depth_bias": 0.25, "editable": ["grip_thickness", "length", "comfort"]}
    if f == "enclosure":
        return {"prior": "hollow_box", "base_shape": "box", "depth_bias": 0.45, "editable": ["wall_thickness", "lid", "mounts"]}
    if f == "adapter":
        return {"prior": "fitting_adapter", "base_shape": "capsule", "depth_bias": 0.24, "editable": ["inner_diameter", "outer_diameter", "length"]}
    return {"prior": "generic_extrude", "base_shape": "box", "depth_bias": 0.2, "editable": ["thickness", "scale"]}
