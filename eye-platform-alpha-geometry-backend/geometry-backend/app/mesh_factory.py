from __future__ import annotations

import json
import math
import re
import struct
import time
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np
import trimesh

Vector3 = Tuple[float, float, float]

SHAPE_PRESETS: Dict[str, Tuple[float, float, float, Tuple[float, float, float, float]]] = {
    "phone": (1.25, 2.25, 0.16, (0.03, 0.75, 0.95, 1.0)),
    "smartphone": (1.25, 2.25, 0.16, (0.03, 0.75, 0.95, 1.0)),
    "bottle": (0.85, 2.1, 0.85, (0.03, 0.85, 0.75, 1.0)),
    "cup": (1.05, 1.35, 1.05, (0.95, 0.95, 0.92, 1.0)),
    "object": (1.25, 1.25, 1.25, (0.1, 0.78, 0.82, 1.0)),
    "cube": (1.3, 1.3, 1.3, (0.1, 0.78, 0.82, 1.0)),
}


def slugify(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", (text or "object").strip().lower()).strip("-")
    return cleaned or "object"


def infer_preset(label: str) -> str:
    lowered = (label or "object").lower()
    if any(x in lowered for x in ["phone", "iphone", "samsung", "mobile"]):
        return "phone"
    if any(x in lowered for x in ["bottle", "spray", "can"]):
        return "bottle"
    if any(x in lowered for x in ["cup", "mug", "vase"]):
        return "cup"
    if "cube" in lowered or "box" in lowered:
        return "cube"
    return "object"


def apply_prompt_dimensions(width: float, height: float, depth: float, prompt: str | None) -> Tuple[float, float, float]:
    p = (prompt or "").lower()
    if "taller" in p or "height" in p or "stretch" in p:
        height *= 1.35
    if "shorter" in p:
        height *= 0.75
    if "wider" in p or "wide" in p:
        width *= 1.25
    if "thinner" in p or "thin" in p or "slim" in p:
        depth *= 0.6
    if "thicker" in p or "stronger" in p or "printable" in p:
        depth *= 1.25
    if "stand" in p or "base" in p:
        width *= 1.25
        depth *= 1.4
    return width, height, depth


def box_vertices(width: float, height: float, depth: float) -> Tuple[List[Vector3], List[int]]:
    x, y, z = width / 2.0, height / 2.0, depth / 2.0
    vertices: List[Vector3] = [
        (-x, -y, z), (x, -y, z), (x, y, z), (-x, y, z),
        (x, -y, -z), (-x, -y, -z), (-x, y, -z), (x, y, -z),
        (-x, y, z), (x, y, z), (x, y, -z), (-x, y, -z),
        (-x, -y, -z), (x, -y, -z), (x, -y, z), (-x, -y, z),
        (x, -y, z), (x, -y, -z), (x, y, -z), (x, y, z),
        (-x, -y, -z), (-x, -y, z), (-x, y, z), (-x, y, -z),
    ]
    indices = [
        0, 1, 2, 0, 2, 3,
        4, 5, 6, 4, 6, 7,
        8, 9, 10, 8, 10, 11,
        12, 13, 14, 12, 14, 15,
        16, 17, 18, 16, 18, 19,
        20, 21, 22, 20, 22, 23,
    ]
    return vertices, indices


def write_glb(path: Path, label: str, width: float, height: float, depth: float, color: Tuple[float, float, float, float]) -> Path:
    vertices, indices = box_vertices(width, height, depth)
    pos_bytes = b"".join(struct.pack("<3f", *v) for v in vertices)
    idx_bytes = b"".join(struct.pack("<H", i) for i in indices)
    while len(pos_bytes) % 4:
        pos_bytes += b"\x00"
    idx_offset = len(pos_bytes)
    bin_blob = pos_bytes + idx_bytes
    while len(bin_blob) % 4:
        bin_blob += b"\x00"

    mins = [min(v[i] for v in vertices) for i in range(3)]
    maxs = [max(v[i] for v in vertices) for i in range(3)]
    gltf = {
        "asset": {"version": "2.0", "generator": "Eye Platform Procedural Geometry"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"name": label or "Object", "mesh": 0, "rotation": [0, 0, 0, 1]}],
        "meshes": [{"name": f"{label or 'Object'} mesh", "primitives": [{"attributes": {"POSITION": 0}, "indices": 1, "material": 0}]}],
        "materials": [{"name": "Eye teal material", "pbrMetallicRoughness": {"baseColorFactor": list(color), "metallicFactor": 0.05, "roughnessFactor": 0.48}}],
        "buffers": [{"byteLength": len(bin_blob)}],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": len(pos_bytes), "target": 34962},
            {"buffer": 0, "byteOffset": idx_offset, "byteLength": len(idx_bytes), "target": 34963},
        ],
        "accessors": [
            {"bufferView": 0, "byteOffset": 0, "componentType": 5126, "count": len(vertices), "type": "VEC3", "min": mins, "max": maxs},
            {"bufferView": 1, "byteOffset": 0, "componentType": 5123, "count": len(indices), "type": "SCALAR"},
        ],
    }
    json_chunk = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    while len(json_chunk) % 4:
        json_chunk += b" "
    total_len = 12 + 8 + len(json_chunk) + 8 + len(bin_blob)
    with path.open("wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, total_len))
        f.write(struct.pack("<I4s", len(json_chunk), b"JSON"))
        f.write(json_chunk)
        f.write(struct.pack("<I4s", len(bin_blob), b"BIN\x00"))
        f.write(bin_blob)
    return path


def _prompt_value(pattern: str, prompt: str) -> float | None:
    match = re.search(pattern, prompt, flags=re.IGNORECASE)
    return float(match.group(1)) if match else None


def _parametric_mesh(label: str, prompt: str | None = None) -> trimesh.Trimesh:
    text = prompt or ""
    preset = infer_preset(f"{label} {text}")
    width, height, depth, _ = SHAPE_PRESETS[preset]
    width, height, depth = [value * 32 for value in (width, height, depth)]
    explicit_height = _prompt_value(r"(\d+(?:\.\d+)?)\s*mm\s*(?:tall|high|height)", text)
    wider_percent = _prompt_value(r"(\d+(?:\.\d+)?)\s*%\s*wider", text)
    if explicit_height is not None:
        height = explicit_height
    if wider_percent is not None:
        width *= 1 + wider_percent / 100
        depth *= 1 + wider_percent / 100
    width, height, depth = apply_prompt_dimensions(width, height, depth, text)
    lowered = text.lower()
    if preset in {"bottle", "cup"} or "cylinder" in lowered:
        radius = max(width, depth) / 2
        if "hole" in lowered:
            return trimesh.creation.annulus(r_min=max(2.0, radius * 0.28), r_max=radius, height=height, sections=64)
        return trimesh.creation.cylinder(radius=radius, height=height, sections=64)
    mesh = trimesh.creation.box(extents=(width, height, depth))
    if "round the edges" in lowered or "rounded edges" in lowered or "fillet" in lowered:
        mesh = mesh.subdivide()
        mesh.vertices *= 0.96
    return mesh


def normalize_and_validate(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    result = mesh.copy()
    result.remove_duplicate_faces()
    result.remove_degenerate_faces()
    result.remove_unreferenced_vertices()
    result.merge_vertices()
    if result.is_empty or len(result.faces) == 0:
        raise ValueError("Generated mesh contains no faces")
    result.apply_translation(-result.bounding_box.centroid)
    if not np.all(np.isfinite(result.extents)) or float(np.max(result.extents)) <= 0:
        raise ValueError("Generated mesh has invalid bounds")
    return result


def export_trimesh(mesh: trimesh.Trimesh, label: str, models_dir: Path) -> Tuple[str, Path]:
    models_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{slugify(label)}-{str(int(time.time() * 1000))[-7:]}.glb"
    path = models_dir / filename
    normalized = normalize_and_validate(mesh)
    normalized.export(path, file_type="glb")
    normalized.export(path.with_suffix(".stl"), file_type="stl")
    return filename, path


def export_glb(label: str, models_dir: Path, prompt: str | None = None) -> Tuple[str, Path]:
    models_dir.mkdir(parents=True, exist_ok=True)
    slug = slugify(label)
    suffix = str(int(time.time() * 1000))[-7:]
    filename = f"{slug}-{suffix}.glb"
    path = models_dir / filename
    return export_trimesh(_parametric_mesh(label, prompt), label, models_dir)
