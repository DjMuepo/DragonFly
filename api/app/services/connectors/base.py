from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Protocol, Dict, Any
from ...core.schemas import LicenseInfo

@dataclass
class RemoteModelCard:
    source: str
    remote_id: str
    title: str
    tags: str
    preview_url: Optional[str]
    file_url: Optional[str]  # may be None for metadata-only
    external_url: Optional[str]  # deep link
    license: LicenseInfo

class SourceConnector(Protocol):
    source: str

    def search(self, query: str, limit: int = 20) -> List[RemoteModelCard]:
        ...

    def fetch(self, remote_id: str) -> Optional[RemoteModelCard]:
        ...

def normalize_license(raw: Dict[str, Any]) -> LicenseInfo:
    # Expect upstream raw dict with possible fields:
    # status: "OK"|"RESTRICTED"|"UNKNOWN"
    # name: e.g. "CC0", "CC-BY-4.0", "GPL", etc.
    # url: license url
    # allow_redistribution: bool
    # allow_commercial: bool
    # require_attribution: bool
    if not raw:
        return LicenseInfo(status="UNKNOWN")
    return LicenseInfo(**raw)
