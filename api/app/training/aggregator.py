from __future__ import annotations
from collections import defaultdict
from typing import Dict, Any, List
import time

from .event_store import read_events
from .feature_store import load_features, save_features
from .rankers import score_event

FAMILIES = ["hook", "bracket", "clip", "handle", "enclosure", "adapter"]

def _ensure_family(features: Dict[str, Any], family: str) -> Dict[str, Any]:
    families = features.setdefault("families", {})
    fam = families.setdefault(family, {
        "min_thickness": None,
        "preferred_material": "PLA",
        "failure_signals": {},
        "success_signals": {},
        "reinforcement_bias": 0.0,
        "fillet_bias": 0.0,
        "sample_weight": 0.0,
    })
    return fam

def aggregate_events(limit: int = 5000) -> Dict[str, Any]:
    events = read_events(limit=limit)
    features = load_features()

    thickness_votes = defaultdict(list)
    material_votes = defaultdict(list)
    reinforcement_score = defaultdict(float)
    fillet_score = defaultdict(float)
    family_weight = defaultdict(float)
    failure_counts = defaultdict(lambda: defaultdict(float))
    success_counts = defaultdict(lambda: defaultdict(float))

    for e in events:
        evt = e.get("event") or ""
        payload = e.get("payload") or {}
        weight = score_event(e)
        family = (payload.get("family") or payload.get("corrected") or payload.get("predicted") or "").lower()
        if family not in FAMILIES:
            continue

        family_weight[family] += weight

        if evt == "structural_strengthen":
            before = payload.get("before") or {}
            after = payload.get("after") or {}
            bt = float(before.get("thickness", 0) or 0)
            at = float(after.get("thickness", 0) or 0)
            if at > 0:
                thickness_votes[family].append((at, weight))
            if bool(after.get("has_rib")) and not bool(before.get("has_rib")):
                reinforcement_score[family] += weight
            if bool(after.get("has_fillet")) and not bool(before.get("has_fillet")):
                fillet_score[family] += weight

        if evt == "print_feedback":
            failure = (payload.get("failure") or "none").lower()
            if failure not in ("", "none"):
                failure_counts[family][failure] += weight

        if evt == "print_outcome_success":
            success_counts[family]["success"] += weight

        if evt == "print_outcome_fail":
            failure_counts[family]["generic_fail"] += weight

        if evt == "review_submit":
            rating = float(payload.get("rating", 0) or 0)
            if rating >= 4:
                success_counts[family]["high_rating"] += weight
            elif rating > 0:
                failure_counts[family]["low_rating"] += weight

        if evt in ("stl_export", "draft_accept"):
            success_counts[family]["accepted"] += weight

        if evt == "draft_reject":
            failure_counts[family]["rejected"] += weight

        material = (payload.get("material") or "").upper()
        if material:
            material_votes[family].append((material, weight))

    for family in FAMILIES:
        fam = _ensure_family(features, family)
        fam["sample_weight"] = round(family_weight[family], 3)

        if thickness_votes[family]:
            weighted_sum = sum(v * w for v, w in thickness_votes[family])
            total_w = sum(w for _, w in thickness_votes[family]) or 1.0
            fam["min_thickness"] = round(weighted_sum / total_w, 4)

        if material_votes[family]:
            material_scores = defaultdict(float)
            for material, w in material_votes[family]:
                material_scores[material] += w
            fam["preferred_material"] = sorted(material_scores.items(), key=lambda kv: kv[1], reverse=True)[0][0]

        if family_weight[family] > 0:
            fam["reinforcement_bias"] = round(reinforcement_score[family] / family_weight[family], 4)
            fam["fillet_bias"] = round(fillet_score[family] / family_weight[family], 4)

        fam["failure_signals"] = {k: round(v, 3) for k, v in sorted(failure_counts[family].items(), key=lambda kv: kv[1], reverse=True)}
        fam["success_signals"] = {k: round(v, 3) for k, v in sorted(success_counts[family].items(), key=lambda kv: kv[1], reverse=True)}

    features["updated_at"] = int(time.time())
    features.setdefault("global", {})["event_count"] = len(events)
    features["global"]["families_covered"] = [f for f in FAMILIES if features["families"].get(f, {}).get("sample_weight", 0) > 0]
    save_features(features)
    return features
