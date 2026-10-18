from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image


def mask_metrics(mask: Path | None, truth: Path | None, details: Path | None, size: tuple[int, int]) -> dict:
    if truth is None:
        return {"measured": False, "reason": "No annotated silhouette; human mask review required."}
    with Image.open(truth) as opened:
        expected = np.asarray(opened.convert("L").resize(size, Image.Resampling.NEAREST)) > 127
    if not expected.any():
        raise ValueError("Expected silhouette must contain foreground.")
    if mask is None:
        predicted = np.ones(expected.shape, dtype=bool)
    else:
        with Image.open(mask) as opened:
            predicted = np.asarray(opened.convert("L").resize(size, Image.Resampling.NEAREST)) > 127
    intersection = int((predicted & expected).sum())
    result = {
        "measured": True,
        "foreground_completeness": intersection / int(expected.sum()),
        "background_contamination": int((predicted & ~expected).sum()) / max(int(predicted.sum()), 1),
        "silhouette_iou": intersection / max(int((predicted | expected).sum()), 1),
        "important_detail_recall": None,
    }
    if details is not None:
        with Image.open(details) as opened:
            important = np.asarray(opened.convert("L").resize(size, Image.Resampling.NEAREST)) > 127
        result["important_detail_recall"] = int((predicted & important).sum()) / int(important.sum()) if important.any() else None
    return result


def inspect_model(path: Path) -> dict:
    import trimesh

    from app.mesh_editing import validate_for_print
    from app.reconstruction_debug import assess_reconstruction

    mesh = trimesh.load(path, force="mesh")
    return {
        "geometric_validity": validate_for_print(mesh, "unknown"),
        "artifact_heuristics": assess_reconstruction(mesh),
        "bounding_box_model_units": mesh.bounds.tolist(),
        "bounding_box_mm": None,
        "visual_similarity": None,
        "silhouette_consistency_3d": None,
        "fidelity_verified": False,
        "review_requirement": "Camera pose and physical scale are unknown. Compare rendered views with the original; valid or watertight geometry is not evidence of fidelity.",
    }