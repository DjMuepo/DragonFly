from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import numpy as np


def save_debug_record(root: Path, job_id: str, fields: dict, image_bytes: bytes | None = None, suffix: str = ".jpg") -> Path:
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    root.chmod(0o700)
    records = sorted(root.glob("*.json"), key=lambda path: path.stat().st_mtime)
    excess = max(0, len(records) - 19)
    for index, record in enumerate(records):
        if time.time() - record.stat().st_mtime > 86400 or index < excess:
            for image in root.glob(f"{record.stem}.input.*"):
                image.unlink(missing_ok=True)
            record.unlink(missing_ok=True)
    identifier = Path(job_id).name
    manifest = root / f"{identifier}.json"
    existing = json.loads(manifest.read_text(encoding="utf-8")) if manifest.exists() else {}
    if image_bytes is not None:
        image_path = root / f"{identifier}.input{suffix}"
        image_path.write_bytes(image_bytes)
        image_path.chmod(0o600)
        fields = {**fields, "submitted_image_path": str(image_path), "submitted_image_sha256": hashlib.sha256(image_bytes).hexdigest(), "submitted_image_bytes": len(image_bytes)}
    manifest.write_text(json.dumps({**existing, **fields}, indent=2), encoding="utf-8")
    manifest.chmod(0o600)
    return manifest


def assess_reconstruction(mesh) -> dict:
    extents = np.asarray(mesh.extents, dtype=float)
    valid_extents = bool(np.all(np.isfinite(extents)) and np.all(extents > 0))
    aspect_ratio = float(extents.max() / extents.min()) if valid_extents else None
    warnings = []
    if not valid_extents:
        warnings.append("Invalid or collapsed model bounds; retake the photo.")
    elif aspect_ratio > 20:
        warnings.append("Unusually extreme model proportions; compare with the photo and retake if incorrect.")
    parts = list(mesh.split(only_watertight=False)) if len(mesh.faces) <= 200000 else None
    large_parts = []
    similar_pairs = []
    if parts is not None:
        area = max(float(mesh.area), 1e-12)
        large_parts = [part for part in parts if float(part.area) / area >= 0.15 and float(part.volume) >= 0]
        if len(large_parts) > 1:
            warnings.append("Multiple large disconnected surfaces detected in a single-object reconstruction; retake the photo.")
        for first_index, first in enumerate(large_parts[:8]):
            for second_index, second in enumerate(large_parts[:8]):
                if second_index <= first_index:
                    continue
                if (np.allclose(np.sort(first.extents), np.sort(second.extents), rtol=0.05, atol=1e-8)
                        and np.isclose(first.area, second.area, rtol=0.05)
                        and np.isclose(abs(first.volume), abs(second.volume), rtol=0.05)):
                    similar_pairs.append([first_index, second_index])
        if similar_pairs:
            warnings.append("Similar-sized disconnected surfaces may be duplicate geometry; inspect before accepting.")
    return {
        "status": "warning" if warnings else "not_flagged",
        "fidelity_verified": False,
        "warnings": warnings,
        "vertices": int(len(mesh.vertices)),
        "faces": int(len(mesh.faces)),
        "connected_surface_count": len(parts) if parts is not None else None,
        "large_disconnected_surfaces": len(large_parts) if parts is not None else None,
        "similar_component_pairs": similar_pairs,
        "bounding_box": mesh.bounds.tolist(),
        "extents": extents.tolist(),
        "aspect_ratio": aspect_ratio,
        "checks_limited": parts is None,
        "limitation": "Heuristics do not detect all fused, mirrored, stacked, or semantic artifacts. Compare the model with the source photo; transparent and reflective objects are especially uncertain.",
    }