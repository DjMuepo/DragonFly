
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict

from PIL import Image, ImageDraw


from app.services.retrieval.index import ensure_schema, upsert_model
from app.core.schemas import LicenseInfo

def make_placeholder_thumb(out_path: Path, title: str) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (512, 512), (20, 20, 24))
    d = ImageDraw.Draw(img)
    text = (title or "model")[:40]
    # simple centered text
    d.text((32, 240), text, fill=(240, 240, 240))
    img.save(out_path, format="PNG")

def load_model_json(p: Path) -> Dict[str, Any]:

    return json.loads(p.read_text(encoding="utf-8"))

def main() -> None:
    ap = argparse.ArgumentParser(description="Ingest a directory of models where each subfolder contains model.json + model file.")
    ap.add_argument("--dir", required=True, help="Directory containing subfolders with model.json")
    args = ap.parse_args()

    root = Path(args.dir).resolve()
    if not root.exists():
        raise SystemExit(f"Directory not found: {root}")

    ensure_schema()
    ingested = 0
    for sub in sorted([p for p in root.iterdir() if p.is_dir()]):
        meta_path = sub / "model.json"
        if not meta_path.exists():
            continue
        meta = load_model_json(meta_path)
        model_id = meta.get("id") or sub.name
        title = meta.get("title") or sub.name
        tags = meta.get("tags") or []
        if isinstance(tags, list):
            tags_str = " ".join(str(t) for t in tags)
        else:
            tags_str = str(tags)

        lic = LicenseInfo(**(meta.get("license") or {"status":"UNKNOWN"}))
        file_rel = meta.get("file") or "model.stl"
        file_path = (sub / file_rel)
        if not file_path.exists():
            print(f"[skip] missing file for {model_id}: {file_path}")
            continue

        # For MVP dev, store file_url as a local relative path under /models-static/... served by FastAPI
        # Copy files into api/static/models/<model_id>/
        static_root = Path(__file__).resolve().parent.parent / "app" / "static" / "models"
        out_dir = static_root / model_id
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / file_path.name
        out_file.write_bytes(file_path.read_bytes())

        file_url = f"/models/{model_id}/{out_file.name}"
        # Thumbnail handling: prefer explicit thumbnail file; otherwise generate a placeholder.
        thumb_rel = meta.get("thumbnail") or meta.get("thumb") or None
        thumb_path = (sub / thumb_rel) if thumb_rel else None
        thumb_out = out_dir / "thumb.png"
        if thumb_path and thumb_path.exists():
            thumb_out.write_bytes(thumb_path.read_bytes())
        else:
            make_placeholder_thumb(thumb_out, title)
        preview_url = f"/models/{model_id}/{thumb_out.name}"


        upsert_model(
            id=model_id,
            source=meta.get("source") or "local-dir",
            title=title,
            tags=tags_str,
            license_info=lic,
            preview_url=preview_url,
            file_url=file_url,
        )
        ingested += 1

    print(f"Ingested {ingested} model(s) from {root}")

if __name__ == "__main__":
    main()
