from __future__ import annotations
from app.preview.preview_service import generate_preview
from typing import Dict, Any, List
from .storage import load_db, save_db, new_id, now_ts

def _slugify(s: str) -> str:
    keep = ''.join(ch.lower() if ch.isalnum() else '-' for ch in (s or 'design'))
    while '--' in keep:
        keep = keep.replace('--','-')
    return keep.strip('-') or 'design'

def publish_design(payload: Dict[str, Any]) -> Dict[str, Any]:
    db = load_db()
    title = payload.get("title") or "Untitled Design"
    design_id = new_id("dsg")
    slug = _slugify(title) + "-" + design_id[-6:]
    preview = generate_preview(slug, title, payload.get("family") or "object", payload.get("creator") or "Anonymous")
    record = {
        "id": design_id,
        "slug": slug,
        "title": title,
        "description": payload.get("description") or "",
        "creator": payload.get("creator") or "Anonymous",
        "owner_id": payload.get("owner_id"),
        "family": payload.get("family") or "object",
        "print_confidence": payload.get("print_confidence"),
        "is_public": bool(payload.get("is_public", True)),
        "created_at": now_ts(),
        "preview_url": payload.get("preview_url") or preview.get("preview_url"),
        "stl_url": payload.get("stl_url"),
        "likes": 0,
        "remix_count": 0,
        "tags": payload.get("tags") or [],
    }
    db["designs"].insert(0, record)
    save_db(db)
    return record

def list_public_designs() -> List[Dict[str, Any]]:
    db = load_db()
    return [d for d in db["designs"] if d.get("is_public")][:100]

def get_design(slug: str) -> Dict[str, Any] | None:
    db = load_db()
    for d in db["designs"]:
        if d.get("slug") == slug:
            return d
    return None

def like_design(slug: str) -> Dict[str, Any] | None:
    db = load_db()
    for d in db["designs"]:
        if d.get("slug") == slug:
            d["likes"] = int(d.get("likes", 0)) + 1
            save_db(db)
            return d
    return None

def seed_if_empty() -> None:
    db = load_db()
    if db["designs"]:
        return
    for s in [
        {"title":"Wall Hook","description":"Simple wall hook design","creator":"Community","family":"hook","print_confidence":92,"is_public":True,"tags":["hook","home"]},
        {"title":"Desk Cable Clip","description":"Clip for desk cable routing","creator":"Community","family":"clip","print_confidence":88,"is_public":True,"tags":["clip","desk"]},
        {"title":"Small Enclosure","description":"Compact project box","creator":"Community","family":"enclosure","print_confidence":85,"is_public":True,"tags":["box","electronics"]},
    ]:
        publish_design(s)


def list_creator_designs(creator: str):
    db = load_db()
    creator_l = (creator or "").strip().lower()
    return [d for d in db["designs"] if (d.get("creator") or "").strip().lower() == creator_l][:100]
