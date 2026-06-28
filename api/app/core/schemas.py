from __future__ import annotations

from typing import List, Literal, Optional
from pydantic import BaseModel, Field

LicenseStatus = Literal["OK", "RESTRICTED", "UNKNOWN"]
Novelty = Literal["COMMON", "SOMEWHAT_UNIQUE", "UNIQUE"]

class LicenseInfo(BaseModel):
    status: LicenseStatus = "UNKNOWN"
    name: Optional[str] = None
    url: Optional[str] = None
    commercial_use_ok: Optional[bool] = None
    attribution_required: Optional[bool] = None
    share_alike: Optional[bool] = None

class MatchCandidate(BaseModel):
    external_url: Optional[str] = None
    hosted: bool = True

    id: str
    source: str
    title: str
    similarity: float = Field(ge=0.0, le=1.0)
    license: LicenseInfo = Field(default_factory=LicenseInfo)
    preview_url: Optional[str] = None

class RetrievalResponse(BaseModel):
    best_match: Optional[MatchCandidate] = None
    max_similarity: float = Field(default=0.0, ge=0.0, le=1.0)

    matches: List[MatchCandidate] = Field(default_factory=list)
    novelty: Optional[Novelty] = None

class SegmentResponse(BaseModel):
    mask_url: str
    confidence: float = Field(ge=0.0, le=1.0)


class StructuralSuggestion(BaseModel):
    id: str
    label: str
    action: dict

class StructuralReport(BaseModel):
    confidence: float
    band: str
    primary_risk: str
    load_type: str
    stress_risk: float
    printability_risk: float
    notes: list[str] = []
    suggestions: list[StructuralSuggestion] = []


class EventLogRequest(BaseModel):
    event: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    job_id: Optional[str] = None
    model_id: Optional[str] = None
    payload: dict = {}

class EventLogResponse(BaseModel):
    ok: bool = True
