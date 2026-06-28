from __future__ import annotations

from typing import Any, Dict, Optional
from app.services.retrieval.index import search

def retrieve_from_image_bytes(data: bytes, *, allow_restricted: bool = False, limit: int = 8):
    return search(query_hint=None, allow_restricted=allow_restricted, limit=limit, image_bytes=data)

def retrieve_from_text(query_hint: str, *, allow_restricted: bool = False, limit: int = 8):
    return search(query_hint=query_hint, allow_restricted=allow_restricted, limit=limit)
