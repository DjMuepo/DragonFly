from __future__ import annotations
import trimesh
from typing import Dict, Any

def _make_box(width: float, height: float, depth: float) -> trimesh.Trimesh:
    return trimesh.creation.box(extents=[width, depth, height])

def _make_hook(params: Dict[str, Any]) -> trimesh.Trimesh:
    width = float(params.get("width", 1.0)); height = float(params.get("height", 0.7)); depth = float(params.get("depth", 0.35)); thickness = float(params.get("thickness", 0.12) or 0.12)
    stem = trimesh.creation.box(extents=[thickness, depth, height]); stem.apply_translation([0, 0, height / 2])
    arm = trimesh.creation.box(extents=[width * 0.55, depth, thickness]); arm.apply_translation([width * 0.22, 0, height - thickness / 2])
    tip = trimesh.creation.box(extents=[thickness, depth, height * 0.3]); tip.apply_translation([width * 0.45, 0, height - height * 0.18])
    return trimesh.util.concatenate([stem, arm, tip])

def _make_bracket(params: Dict[str, Any]) -> trimesh.Trimesh:
    width = float(params.get("width", 1.0)); height = float(params.get("height", 0.7)); depth = float(params.get("depth", 0.35)); thickness = float(params.get("thickness", 0.12) or 0.12)
    base = trimesh.creation.box(extents=[width * 0.7, depth, thickness]); base.apply_translation([width * 0.12, 0, thickness / 2])
    wall = trimesh.creation.box(extents=[thickness, depth, height]); wall.apply_translation([-width * 0.18, 0, height / 2])
    return trimesh.util.concatenate([base, wall])

def _make_clip(params: Dict[str, Any]) -> trimesh.Trimesh:
    width = float(params.get("width", 0.8)); height = float(params.get("height", 0.8)); depth = float(params.get("depth", 0.25)); thickness = float(params.get("thickness", 0.1) or 0.1)
    spine = trimesh.creation.box(extents=[thickness, depth, height]); spine.apply_translation([0, 0, height / 2])
    jaw_top = trimesh.creation.box(extents=[width * 0.4, depth, thickness]); jaw_top.apply_translation([width * 0.18, 0, height - thickness / 2])
    jaw_bottom = trimesh.creation.box(extents=[width * 0.25, depth, thickness]); jaw_bottom.apply_translation([width * 0.1, 0, thickness / 2])
    return trimesh.util.concatenate([spine, jaw_top, jaw_bottom])

def _make_handle(params: Dict[str, Any]) -> trimesh.Trimesh:
    length = float(params.get("length", 1.0)); grip = float(params.get("grip_thickness", 0.25) or 0.25)
    return trimesh.creation.capsule(height=max(0.2, length - grip), radius=max(0.08, grip / 2))

def _make_enclosure(params: Dict[str, Any]) -> trimesh.Trimesh:
    width = float(params.get("width", 1.0)); height = float(params.get("height", 0.7)); depth = float(params.get("depth", 0.5))
    return trimesh.creation.box(extents=[width, depth, height])

def _make_adapter(params: Dict[str, Any]) -> trimesh.Trimesh:
    outer_d = float(params.get("outer_diameter", 0.5) or 0.5); length = float(params.get("length", 0.8) or 0.8)
    return trimesh.creation.cylinder(radius=max(0.05, outer_d/2), height=length, sections=32)

def mesh_from_parametric(parametric: Dict[str, Any]) -> trimesh.Trimesh:
    params = dict(parametric.get("params") or {})
    family = (parametric.get("family") or "generic").lower()
    if family == "hook":
        mesh = _make_hook(params)
    elif family == "bracket":
        mesh = _make_bracket(params)
    elif family == "clip":
        mesh = _make_clip(params)
    elif family == "handle":
        mesh = _make_handle(params)
    elif family == "enclosure":
        mesh = _make_enclosure(params)
    elif family == "adapter":
        mesh = _make_adapter(params)
    else:
        mesh = _make_box(float(params.get("width", 1.0)), float(params.get("height", 0.7)), float(params.get("depth", 0.3)))
    mesh.remove_duplicate_faces()
    mesh.remove_unreferenced_vertices()
    mesh.process(validate=True)
    return mesh

def export_parametric_stl(parametric: Dict[str, Any], out_path: str) -> Dict[str, Any]:
    mesh = mesh_from_parametric(parametric)
    mesh.export(out_path)
    return {"ok": True, "out_path": out_path, "is_watertight": bool(mesh.is_watertight), "faces": int(len(mesh.faces)), "vertices": int(len(mesh.vertices)), "bounds": mesh.bounds.tolist()}
