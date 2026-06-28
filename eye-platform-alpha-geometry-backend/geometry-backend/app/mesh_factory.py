from __future__ import annotations

import math
import re
import uuid
from pathlib import Path
from typing import Tuple

import numpy as np
import trimesh

Color = Tuple[int, int, int, int]
CYAN: Color = (24, 198, 209, 255)
PURPLE: Color = (91, 95, 151, 255)
ORANGE: Color = (255, 136, 77, 255)
GRAY: Color = (180, 185, 198, 255)
DARK: Color = (45, 51, 72, 255)
WHITE: Color = (240, 245, 250, 255)


def _slug(label: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", label.strip().lower()).strip("-")
    return cleaned or "object"


def _paint(mesh: trimesh.Trimesh, color: Color) -> trimesh.Trimesh:
    mesh.visual.vertex_colors = np.tile(np.array(color, dtype=np.uint8), (len(mesh.vertices), 1))
    return mesh


def _move(mesh: trimesh.Trimesh, xyz) -> trimesh.Trimesh:
    mesh.apply_translation(xyz)
    return mesh


def _scale(mesh: trimesh.Trimesh, xyz) -> trimesh.Trimesh:
    mesh.apply_scale(xyz)
    return mesh


def _box(extents, color: Color, translate=(0, 0, 0)) -> trimesh.Trimesh:
    return _move(_paint(trimesh.creation.box(extents=extents), color), translate)


def _cylinder(radius=0.5, height=1.0, color: Color = CYAN, translate=(0, 0, 0), sections=48) -> trimesh.Trimesh:
    # trimesh cylinders are aligned on Z. Rotate to make Z height feel upright in common GLB viewers.
    mesh = trimesh.creation.cylinder(radius=radius, height=height, sections=sections)
    return _move(_paint(mesh, color), translate)


def _sphere(radius=0.65, color: Color = CYAN, translate=(0, 0, 0)) -> trimesh.Trimesh:
    return _move(_paint(trimesh.creation.icosphere(subdivisions=3, radius=radius), color), translate)


def _spray_bottle() -> trimesh.Scene:
    parts = []
    parts.append(_cylinder(0.36, 1.55, CYAN, (0, 0, 0)))
    parts.append(_cylinder(0.22, 0.35, WHITE, (0, 0, 0.95)))
    parts.append(_box((0.75, 0.28, 0.22), DARK, (0.26, 0, 1.24)))
    parts.append(_box((0.22, 0.18, 0.48), DARK, (-0.15, 0, 1.03)))
    nozzle = _cylinder(0.07, 0.55, ORANGE, (0.68, 0, 1.25), 24)
    nozzle.apply_transform(trimesh.transformations.rotation_matrix(math.radians(90), [0, 1, 0]))
    parts.append(nozzle)
    return trimesh.Scene(parts)


def _bottle() -> trimesh.Scene:
    parts = []
    parts.append(_cylinder(0.34, 1.55, CYAN, (0, 0, 0)))
    parts.append(_cylinder(0.20, 0.55, WHITE, (0, 0, 1.05)))
    parts.append(_cylinder(0.23, 0.16, ORANGE, (0, 0, 1.45)))
    return trimesh.Scene(parts)


def _box_object() -> trimesh.Scene:
    parts = [_box((1.15, 0.9, 1.25), PURPLE, (0, 0, 0)), _box((1.18, 0.05, 0.08), WHITE, (0, 0.48, 0.25))]
    return trimesh.Scene(parts)


def _mug() -> trimesh.Scene:
    cup = _cylinder(0.48, 1.0, ORANGE, (0, 0, 0))
    handle = trimesh.creation.torus(major_radius=0.32, minor_radius=0.055, major_sections=48, minor_sections=12)
    handle.apply_transform(trimesh.transformations.rotation_matrix(math.radians(90), [1, 0, 0]))
    handle.apply_scale((0.8, 1.0, 1.15))
    _paint(handle, WHITE)
    _move(handle, (0.5, 0, 0.05))
    return trimesh.Scene([cup, handle])


def _phone() -> trimesh.Scene:
    body = _box((0.72, 0.08, 1.35), DARK, (0, 0, 0))
    screen = _box((0.62, 0.02, 1.16), CYAN, (0, -0.052, 0.02))
    return trimesh.Scene([body, screen])


def _chair() -> trimesh.Scene:
    parts = [
        _box((1.05, 0.95, 0.13), CYAN, (0, 0, 0.05)),
        _box((1.05, 0.12, 1.1), PURPLE, (0, 0.42, 0.62)),
        _box((0.12, 0.12, 0.9), DARK, (-0.42, -0.35, -0.42)),
        _box((0.12, 0.12, 0.9), DARK, (0.42, -0.35, -0.42)),
        _box((0.12, 0.12, 0.9), DARK, (-0.42, 0.35, -0.42)),
        _box((0.12, 0.12, 0.9), DARK, (0.42, 0.35, -0.42)),
    ]
    return trimesh.Scene(parts)


def _generic() -> trimesh.Scene:
    base = _sphere(0.58, CYAN, (0, 0, 0.1))
    pedestal = _cylinder(0.34, 0.5, PURPLE, (0, 0, -0.48))
    return trimesh.Scene([base, pedestal])


def make_scene_for_label(label: str) -> trimesh.Scene:
    lower = (label or "object").lower()
    if "spray" in lower:
        return _spray_bottle()
    if "bottle" in lower or "container" in lower:
        return _bottle()
    if "box" in lower or "package" in lower or "tissue" in lower:
        return _box_object()
    if "mug" in lower or "cup" in lower:
        return _mug()
    if "phone" in lower or "mobile" in lower:
        return _phone()
    if "chair" in lower or "seat" in lower:
        return _chair()
    return _generic()


def export_glb(label: str, out_dir: Path) -> tuple[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    safe = _slug(label)
    filename = f"{safe}-{uuid.uuid4().hex[:8]}.glb"
    out_path = out_dir / filename
    scene = make_scene_for_label(label)
    scene.export(out_path, file_type="glb")
    return filename, out_path
