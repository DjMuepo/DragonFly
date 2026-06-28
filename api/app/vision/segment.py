from __future__ import annotations

import io
from typing import Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

try:
    import cv2  # type: ignore
except Exception:
    cv2 = None


def _fallback_center_mask(image_bytes: bytes) -> bytes:
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    w, h = img.size
    mask = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(mask)
    margin_x = int(w * 0.12)
    margin_y = int(h * 0.12)
    d.rounded_rectangle(
        [margin_x, margin_y, w - margin_x, h - margin_y],
        radius=int(min(w, h) * 0.06),
        fill=255,
    )
    mask = mask.filter(ImageFilter.GaussianBlur(radius=max(2, int(min(w, h) * 0.008))))
    out = io.BytesIO()
    mask.save(out, format="PNG")
    return out.getvalue()


def _mask_to_png(mask_arr: np.ndarray) -> bytes:
    mask = Image.fromarray(mask_arr.astype(np.uint8), mode="L")
    out = io.BytesIO()
    mask.save(out, format="PNG")
    return out.getvalue()


def grabcut_mask(image_bytes: bytes) -> Optional[bytes]:
    if cv2 is None:
        return None

    try:
        pil = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img = np.array(pil)
        img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

        h, w = img_bgr.shape[:2]
        if h < 10 or w < 10:
            return None

        # centered rectangle prior
        rect = (
            int(w * 0.08),
            int(h * 0.08),
            max(1, int(w * 0.84)),
            max(1, int(h * 0.84)),
        )

        mask = np.zeros((h, w), np.uint8)
        bgd = np.zeros((1, 65), np.float64)
        fgd = np.zeros((1, 65), np.float64)

        cv2.grabCut(img_bgr, mask, rect, bgd, fgd, 4, cv2.GC_INIT_WITH_RECT)
        fg = np.where((mask == 1) | (mask == 3), 255, 0).astype("uint8")

        # Clean up mask a bit
        kernel = np.ones((5, 5), np.uint8)
        fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, kernel)
        fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, kernel)
        fg = cv2.GaussianBlur(fg, (5, 5), 0)

        return _mask_to_png(fg)
    except Exception:
        return None


def simple_center_mask(image_bytes: bytes) -> bytes:
    # Better quality path first
    gc = grabcut_mask(image_bytes)
    if gc is not None:
        return gc
    return _fallback_center_mask(image_bytes)


def apply_mask_preview(image_bytes: bytes, mask_bytes: bytes) -> bytes:
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    mask = Image.open(io.BytesIO(mask_bytes)).convert("L").resize(img.size)
    bg = Image.new("RGBA", img.size, (10, 10, 10, 255))
    comp = Image.composite(img, bg, mask)
    out = io.BytesIO()
    comp.save(out, format="PNG")
    return out.getvalue()
