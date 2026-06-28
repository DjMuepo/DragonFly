from __future__ import annotations
import io

import os
import time
from typing import Optional, Tuple

from PIL import Image, ImageDraw

def _load_image_bytes(content: bytes) -> Image.Image:
    return Image.open(io.BytesIO(content)).convert("RGB")

def _center_rect_mask(size: Tuple[int, int]) -> Image.Image:
    w, h = size
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    # Central rectangle (placeholder for real segmentation).
    pad_w = int(w * 0.2)
    pad_h = int(h * 0.2)
    draw.rectangle([pad_w, pad_h, w - pad_w, h - pad_h], fill=255)
    return mask

def _tap_circle_mask(size: Tuple[int, int], tap_x: float, tap_y: float) -> Image.Image:
    w, h = size
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    r = int(min(w, h) * 0.25)
    cx = int(max(0, min(w-1, tap_x)))
    cy = int(max(0, min(h-1, tap_y)))
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    return mask

def write_mask_png(mask: Image.Image, out_path: str) -> None:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    mask.save(out_path, format="PNG")