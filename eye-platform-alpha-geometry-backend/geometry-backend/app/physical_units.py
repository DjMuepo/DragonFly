from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import trimesh

from .mesh_factory import normalize_and_validate, slugify


UNIT_TO_MM = {
    "mm": 1.0,
    "millimeter": 1.0,
    "millimeters": 1.0,
    "cm": 10.0,
    "centimeter": 10.0,
    "centimeters": 10.0,
    "in": 25.4,
    "inch": 25.4,
    "inches": 25.4,
    "m": 1000.0,
    "meter": 1000.0,
    "meters": 1000.0,
}
AXIS_NAMES = {"width": 0, "wide": 0, "depth": 1, "deep": 1, "height": 2, "high": 2, "tall": 2}


@dataclass(frozen=True)
class ScaleMetadata:
    status: str = "unknown"
    canonical_unit: str = "mm"
    glb_unit: str = "meter"
    calibrated_axis: str | None = None
    calibrated_value_mm: float | None = None
    source_measurement: str | None = None


def metadata_path(model_path: Path) -> Path:
    return model_path.with_suffix(".metadata.json")


def save_scale_metadata(model_path: Path, metadata: ScaleMetadata) -> None:
    metadata_path(model_path).write_text(json.dumps(asdict(metadata), separators=(",", ":")), encoding="utf-8")


def load_scale_metadata(model_path: Path) -> ScaleMetadata:
    path = metadata_path(model_path)
    if not path.is_file():
        return ScaleMetadata()
    try:
        return ScaleMetadata(**json.loads(path.read_text(encoding="utf-8")))
    except (TypeError, ValueError, json.JSONDecodeError):
        return ScaleMetadata()


def parse_known_measurement(text: str) -> tuple[int, str, float]:
    cleaned = text.lower().strip()
    match = re.search(
        r"(\d+(?:\.\d+)?)\s*(mm|millimeters?|cm|centimeters?|inches?|in|m|meters?)\s*(?:in\s+)?(?:total\s+)?(width|wide|depth|deep|height|high|tall)",
        cleaned,
    )
    if not match:
        match = re.search(
            r"(width|wide|depth|deep|height|high|tall)(?:\s+is|\s+of|\s*=)?\s*(\d+(?:\.\d+)?)\s*(mm|millimeters?|cm|centimeters?|inches?|in|m|meters?)",
            cleaned,
        )
        if not match:
            raise ValueError("Enter one known dimension, for example: This bottle is 180 mm tall.")
        word, value, unit = match.group(1), float(match.group(2)), match.group(3)
    else:
        value, unit, word = float(match.group(1)), match.group(2), match.group(3)
    value_mm = value * UNIT_TO_MM[unit]
    if not 0.1 <= value_mm <= 100000:
        raise ValueError("The known measurement must be between 0.1 mm and 100 m.")
    axis = AXIS_NAMES[word]
    return axis, ("width", "depth", "height")[axis], value_mm


def mesh_from_glb_for_edit(model_path: Path, metadata: ScaleMetadata) -> trimesh.Trimesh:
    mesh = trimesh.load(model_path, force="mesh")
    if metadata.status == "calibrated":
        mesh.apply_scale(1000.0)
    return mesh


def export_manufacturing_mesh(mesh_mm: trimesh.Trimesh, label: str, models_dir: Path, metadata: ScaleMetadata, center: bool = False) -> tuple[str, Path]:
    models_dir.mkdir(parents=True, exist_ok=True)
    normalized_mm = normalize_and_validate(mesh_mm, center=center)
    filename = f"{slugify(label)}-{str(int(time.time() * 1000))[-7:]}.glb"
    glb_path = models_dir / filename
    glb_mesh = normalized_mm.copy()
    glb_mesh.apply_scale(0.001)
    glb_mesh.export(glb_path, file_type="glb")
    normalized_mm.export(glb_path.with_suffix(".stl"), file_type="stl")
    save_scale_metadata(glb_path, metadata)
    return filename, glb_path


def calibrate_mesh(source_glb: Path, measurement: str) -> tuple[trimesh.Trimesh, ScaleMetadata]:
    raw = trimesh.load(source_glb, force="mesh")
    axis, axis_name, value_mm = parse_known_measurement(measurement)
    current = float(raw.extents[axis])
    if current <= 0:
        raise ValueError(f"The model has no measurable {axis_name}.")
    raw.apply_scale(value_mm / current)
    metadata = ScaleMetadata(
        status="calibrated",
        calibrated_axis=axis_name,
        calibrated_value_mm=round(value_mm, 6),
        source_measurement=measurement.strip(),
    )
    return raw, metadata
