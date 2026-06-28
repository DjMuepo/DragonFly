from __future__ import annotations
from typing import Dict, Any

HIGH_VALUE_EVENTS = {
    "family_correction": 5.0,
    "draft_reject": 4.0,
    "print_outcome_fail": 4.5,
    "print_feedback": 3.5,
    "draft_accept": 2.5,
    "review_submit": 2.5,
    "design_publish": 1.8,
    "stl_export": 1.5,
    "structural_strengthen": 3.0,
    "profile_onboarding_save": 1.2,
    "useful_yes": 1.8,
    "useful_no": 2.0,
    "print_outcome_success": 3.5,
}

def score_event(event: Dict[str, Any]) -> float:
    evt = event.get("event") or ""
    score = HIGH_VALUE_EVENTS.get(evt, 0.5)
    payload = event.get("payload") or {}
    if evt == "review_submit":
        score += float(payload.get("rating", 0) or 0) * 0.2
    if evt == "print_feedback" and (payload.get("failure") not in (None, "", "none")):
        score += 1.0
    if evt == "family_correction":
        predicted = (payload.get("predicted") or "").lower()
        corrected = (payload.get("corrected") or "").lower()
        if predicted and corrected and predicted != corrected:
            score += 1.0
    return round(score, 3)
