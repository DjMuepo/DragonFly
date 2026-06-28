from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from .base import RemoteModelCard, SourceConnector, normalize_license

class ThangsConnector(SourceConnector):
    source = "thangs"

    def __init__(self) -> None:
        self._data_path = Path(__file__).resolve().parent / "samples" / "thangs.json"
        self._rows = json.loads(self._data_path.read_text(encoding="utf-8"))

    def search(self, query: str, limit: int = 20) -> List[RemoteModelCard]:
        q = (query or "").lower().strip()
        out: List[RemoteModelCard] = []
        for r in self._rows:
            hay = (r.get("title","") + " " + r.get("tags","")).lower()
            if (not q) or (q in hay):
                out.append(self._to_card(r))
        return out[:limit]

    def fetch(self, remote_id: str) -> Optional[RemoteModelCard]:
        for r in self._rows:
            if r.get("remote_id") == remote_id:
                return self._to_card(r)
        return None

    def _to_card(self, r: dict) -> RemoteModelCard:
        return RemoteModelCard(
            source=self.source,
            remote_id=r.get("remote_id",""),
            title=r.get("title",""),
            tags=r.get("tags",""),
            preview_url=r.get("preview_url"),
            file_url=r.get("file_url"),
            external_url=r.get("external_url"),
            license=normalize_license(r.get("license") or {}),
        )
