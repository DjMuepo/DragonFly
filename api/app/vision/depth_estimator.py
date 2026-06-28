from __future__ import annotations
import io
from typing import Dict, Any
from PIL import Image, ImageFilter, ImageOps
import numpy as np

def estimate_depth_map(image_bytes: bytes) -> Dict[str, Any]:
    img = Image.open(io.BytesIO(image_bytes)).convert("L")
    img = ImageOps.autocontrast(img)
    depth = img.filter(ImageFilter.GaussianBlur(radius=3))
    arr = np.array(depth, dtype=np.float32) / 255.0
    h, w = arr.shape
    center = float(arr[h//4:3*h//4, w//4:3*w//4].mean())
    edges = float(np.concatenate([
        arr[:max(1,h//8), :].ravel(),
        arr[-max(1,h//8):, :].ravel(),
        arr[:, :max(1,w//8)].ravel(),
        arr[:, -max(1,w//8):].ravel(),
    ]).mean())
    return {"depth_center": round(center, 4), "depth_edges": round(edges, 4), "depth_contrast": round(abs(center - edges), 4), "confidence": 0.42, "notes": ["Lightweight monocular depth fallback.", "Production depth model comes later."]}
