from __future__ import annotations

import io
from typing import Dict, Any
from PIL import Image, ImageOps, ImageFilter, ImageChops

def generate_preview_png(image_bytes: bytes, mask_bytes: bytes, draft: Dict[str, Any]) -> bytes:
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    mask = Image.open(io.BytesIO(mask_bytes)).convert("L").resize(img.size)
    obj = Image.new("RGBA", img.size, (0, 0, 0, 0))
    obj.paste(img, (0, 0), mask)

    # create pseudo-3D extrusion with offset shadow layers based on estimated depth
    depth_ratio = float(draft.get("estimated_depth_ratio", 0.2) or 0.2)
    steps = max(4, min(18, int(6 + depth_ratio * 24)))

    canvas = Image.new("RGBA", img.size, (14, 14, 18, 255))
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))

    alpha = mask.filter(ImageFilter.GaussianBlur(radius=1.2))
    for i in range(steps, 0, -1):
        off = int(i * 2)
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        shade = max(25, 120 - i * 4)
        layer.paste((shade, shade, shade + 10, 120), (off, off), alpha)
        shadow = Image.alpha_composite(shadow, layer)

    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=2.5))
    canvas = Image.alpha_composite(canvas, shadow)

    # simple edge highlight
    edge = ImageOps.colorize(alpha, black="#000000", white="#d9d9e3").convert("RGBA")
    edge.putalpha(alpha.point(lambda p: min(110, int(p * 0.35))))
    canvas = Image.alpha_composite(canvas, edge)

    # front object
    canvas = Image.alpha_composite(canvas, obj)

    out = io.BytesIO()
    canvas.save(out, format="PNG")
    return out.getvalue()
