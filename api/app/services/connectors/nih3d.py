from __future__ import annotations

import os
import re
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

from .base import RemoteModelCard, SourceConnector
from ..core.schemas import LicenseInfo

NIH_BASE = "https://3d.nih.gov"

def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())

def _license_from_text(t: str) -> LicenseInfo:
    tl = (t or "").lower()
    # NIH entries vary; try to detect common CC license strings
    if "cc0" in tl or "public domain" in tl:
        return LicenseInfo(status="OK", name="CC0", allow_redistribution=True, allow_commercial=True, require_attribution=False)
    if "cc-by" in tl:
        return LicenseInfo(status="OK", name="CC-BY", allow_redistribution=True, allow_commercial=True, require_attribution=True)
    if "noncommercial" in tl or "nc" in tl:
        return LicenseInfo(status="RESTRICTED", name="CC-NC", allow_redistribution=False, allow_commercial=False, require_attribution=True)
    if "no derivatives" in tl or "nd" in tl:
        return LicenseInfo(status="RESTRICTED", name="CC-ND", allow_redistribution=False, allow_commercial=False, require_attribution=True)
    return LicenseInfo(status="UNKNOWN")

class Nih3DConnector(SourceConnector):
    """NIH 3D Print Exchange connector.

    This connector intentionally ingests metadata and deep links. File hosting should be gated by your policy.
    """
    source = "nih3d"

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": os.getenv("EYE_UA", "Muepo-Eye/0.1")})

    def search(self, query: str, limit: int = 20) -> List[RemoteModelCard]:
        # NIH site search endpoints are not documented here; use metadata-only stub search for now.
        # For real ingestion, prefer ingest by IDs or collection seeds.
        return []

    def fetch(self, remote_id: str) -> Optional[RemoteModelCard]:
        # remote_id like 3DPX-021858
        rid = remote_id.strip()
        if not rid:
            return None
        url = f"{NIH_BASE}/entries/{rid}"
        r = self.session.get(url, timeout=20)
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, "html.parser")
        title = _clean((soup.find("h1") or soup.find("title") or {}).get_text() if soup else rid)
        # tags/category: try to locate metadata list
        text = soup.get_text(" ", strip=True)
        # crude tag extraction; refined later
        tags = ""
        # license: look for 'License' label in page text
        lic_match = re.search(r"License\s*[:\-]?\s*([A-Za-z0-9\-\s\(\)\+\/\.]+)", text, re.IGNORECASE)
        lic = _license_from_text(lic_match.group(1) if lic_match else "")
        # preview image: try OG image
        preview_url = None
        og = soup.find("meta", attrs={"property": "og:image"})
        if og and og.get("content"):
            preview_url = og.get("content")
        # download link (external)
        file_url = None
        dl = soup.find("a", string=re.compile("Download", re.IGNORECASE))
        if dl and dl.get("href"):
            href = dl.get("href")
            if href.startswith("/"):
                href = NIH_BASE + href
            file_url = href
        return RemoteModelCard(
            source=self.source,
            remote_id=rid,
            title=title,
            tags=tags,
            preview_url=preview_url,
            file_url=file_url,
            external_url=url,
            license=lic,
        )
