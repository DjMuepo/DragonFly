import os, json, time, uuid

DATA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "share_funnel.json"))

def _load():
    if not os.path.exists(DATA_PATH):
        data = {"links": []}
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return data
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def _save(data):
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def create_share_link(payload):
    data = _load()
    slug = payload.get("slug") or ("design-" + uuid.uuid4().hex[:8])
    link = {
        "id": "lnk_" + uuid.uuid4().hex[:10],
        "slug": slug,
        "title": payload.get("title") or "Untitled Design",
        "creator": payload.get("creator") or "Anonymous",
        "preview_url": payload.get("preview_url") or "",
        "deep_link": payload.get("deep_link") or f"eyeplatform://design/{slug}",
        "created_at": int(time.time()),
    }
    data["links"].insert(0, link)
    _save(data)
    return {"ok": True, "link": link}

def list_share_links(limit=100):
    return {"ok": True, "links": (_load().get("links") or [])[:limit]}
