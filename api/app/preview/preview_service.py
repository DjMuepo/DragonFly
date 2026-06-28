from __future__ import annotations
import os, time, shutil
from typing import Dict, Any
from PIL import Image, ImageDraw

PREVIEW_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "design_previews"))
PUBLIC_PREVIEW_BASE = os.environ.get("PREVIEW_PUBLIC_BASE", "https://example.com/previews")
os.makedirs(PREVIEW_DIR, exist_ok=True)

def _safe_name(slug: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-","_") else "-" for ch in (slug or "design"))

def generate_preview(slug: str, title: str, family: str = "object", creator: str = "Anonymous") -> Dict[str, Any]:
    slug = _safe_name(slug)
    path = os.path.join(PREVIEW_DIR, f"{slug}.png")
    img = Image.new("RGB", (1200, 630), (20, 20, 20))
    d = ImageDraw.Draw(img)
    d.rectangle((40, 40, 1160, 590), outline=(60, 60, 60), width=2)
    d.text((70, 110), f"{title[:60]}", fill=(255,255,255))
    d.text((70, 180), f"Family: {family}", fill=(190,190,190))
    d.text((70, 220), f"Creator: {creator}", fill=(190,190,190))
    d.text((70, 500), "AI-guided 3D design • Eye Platform", fill=(160,160,160))
    img.save(path)
    return {
        "slug": slug,
        "preview_path": path,
        "preview_url": f"{PUBLIC_PREVIEW_BASE}/{slug}.png",
        "generated_at": int(time.time())
    }

def upload_preview_local(slug: str) -> Dict[str, Any]:
    slug = _safe_name(slug)
    src = os.path.join(PREVIEW_DIR, f"{slug}.png")
    if not os.path.exists(src):
        raise FileNotFoundError("preview not found")
    hosted_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "hosted_previews"))
    os.makedirs(hosted_dir, exist_ok=True)
    dst = os.path.join(hosted_dir, f"{slug}.png")
    shutil.copyfile(src, dst)
    return {"ok": True, "hosted_path": dst, "preview_url": f"{PUBLIC_PREVIEW_BASE}/{slug}.png"}
