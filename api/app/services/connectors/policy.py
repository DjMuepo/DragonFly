from __future__ import annotations

import os
from typing import Tuple
from ...core.schemas import LicenseInfo

# Commercial-friendly default:
# Allow: CC0/Public Domain/CC-BY (with attribution)
# Block: NC/ND by default (treated as RESTRICTED)
ALLOW_CC_BY = os.getenv("EYE_ALLOW_CC_BY", "1") == "1"

def classify_license(lic: LicenseInfo) -> Tuple[bool, str]:
    """Return (is_allowed_to_host, reason).
    Hosting means: downloading and re-serving files from our platform.
    If not allowed to host, we may still index metadata + deep link.
    """
    name = (lic.name or "").lower()
    status = (lic.status or "UNKNOWN").upper()

    if status == "RESTRICTED":
        return (False, "restricted")
    if "cc0" in name or "public domain" in name:
        return (True, "open")
    if "cc-by" in name:
        return (ALLOW_CC_BY, "cc-by" if ALLOW_CC_BY else "cc-by-blocked")
    # Default conservative:
    return (False, "unknown-or-nonredistributable")

def allow_in_results(lic: LicenseInfo, allow_restricted: bool) -> bool:
    if (lic.status or "UNKNOWN").upper() == "RESTRICTED":
        return bool(allow_restricted)
    return True
