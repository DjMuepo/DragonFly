from __future__ import annotations

import io
from pathlib import Path
from typing import Dict, Any
from PIL import Image

def generate_basic_draft(mask_bytes: bytes, *, object_family: str = "object", depth_scale: float = 1.0) -> Dict[str, Any]:
    # Placeholder single-view draft metadata generator.
    # For now, returns bounding-box-derived dimensions and a rough "extrude" strategy.
    img = Image.open(io.BytesIO(mask_bytes)).convert("L")
    bbox = img.getbbox() or (0, 0, img.size[0], img.size[1])
    x0, y0, x1, y1 = bbox
    w = max(1, x1 - x0)
    h = max(1, y1 - y0)
    aspect = round(w / max(1, h), 3)
    # rough family-based depth prior
    depth_prior = {
        "bracket": 0.22, "hook": 0.18, "clip": 0.16, "handle": 0.25,
        "container": 0.45, "phone stand": 0.28, "mechanical part": 0.24,
        "adapter": 0.25, "connector": 0.2, "chair": 0.4, "desk": 0.35,
    }
    family = (object_family or "object").lower()
    depth_ratio = depth_prior.get(family, 0.2) * depth_scale
    return {
        "strategy": "silhouette_extrude",
        "object_family": object_family,
        "bbox": {"x0": x0, "y0": y0, "x1": x1, "y1": y1},
        "aspect_ratio": aspect,
        "estimated_depth_ratio": round(depth_ratio, 3),
        "confidence": 0.45 if family not in depth_prior else 0.62,
        "notes": [
            "Single-view draft uses silhouette + depth prior.",
            "Back side estimated.",
            "Edit before printing."
        ],
    }
