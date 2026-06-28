from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Literal
import math

from app.services.structural.policy_nn import (
    encode_features, PolicyNet, predict_action, apply_action,
    latest_model_path, versioned_model_path,
    load_events_jsonl, build_training_rows, train_policy, save_model,
)
import os

LoadType = Literal["Compression","Tension","Shear","Bending","Torsion","Multi-axis","Unknown"]
RiskType = Literal["Bending","Shear","Torsion","Compression","Tension","Printability","Unknown"]

@dataclass
class StructuralSuggestion:
    id: str
    label: str
    action: Dict[str, Any]  # e.g. {"type":"thickness","delta":0.15}

@dataclass
class StructuralReport:
    confidence: float  # 0-100
    band: Literal["GREEN","YELLOW","RED"]
    primary_risk: RiskType
    load_type: LoadType
    stress_risk: float  # 0-100
    printability_risk: float  # 0-100
    notes: List[str]
    suggestions: List[StructuralSuggestion]

def _clamp(x: float, a: float, b: float) -> float:
    return max(a, min(b, x))

def _band(score: float) -> str:
    if score >= 80: return "GREEN"
    if score >= 50: return "YELLOW"
    return "RED"

def analyze_from_simple_params(params: Dict[str, Any]) -> StructuralReport:
    """Heuristic analyzer for MVP.
    Params may include: thickness (0..1 or mm), scale, has_fillet, has_rib, hole_count, overhang_risk (0..1),
    joint_type, aspect_ratio, cantilever (0..1)
    """
    thickness = float(params.get("thickness", 1.0))
    scale = float(params.get("scale", 1.0))
    has_fillet = bool(params.get("has_fillet", False))
    has_rib = bool(params.get("has_rib", False))
    hole_count = int(params.get("hole_count", 0))
    overhang = float(params.get("overhang_risk", 0.0))
    cantilever = float(params.get("cantilever", 0.0))
    aspect = float(params.get("aspect_ratio", 1.0))
    joint = str(params.get("joint_type", "unknown")).lower()

    # Normalize thickness: treat <=0 as 1
    t = max(0.1, thickness)
    # Risks (0..100)
    bending_risk = _clamp((cantilever*70 + (aspect-1)*10 + (1.2 - min(t,1.2))*30), 0, 100)
    shear_risk = _clamp((hole_count*6 + (1.0 - min(t,1.0))*25), 0, 100)
    torsion_risk = _clamp(((1.0 - min(t,1.0))*35 + (joint in ["press-fit","snap-fit"])*10), 0, 100)
    stress_risk = _clamp((hole_count*5 + (0 if has_fillet else 18) + (0 if has_rib else 10)), 0, 100)
    printability_risk = _clamp(overhang*100 + (0.8 - min(t,0.8))*40, 0, 100)

    # Joint integrity bonus
    joint_bonus = 0
    if "bolt" in joint or "thread" in joint:
        joint_bonus = 10
    elif "snap" in joint:
        joint_bonus = 0
    elif "press" in joint:
        joint_bonus = 2

    reinforcement_bonus = (12 if has_rib else 0) + (8 if has_fillet else 0)
    thickness_bonus = _clamp((t-1.0)*25, -15, 25)

    # overall score
    base = 85 + joint_bonus + reinforcement_bonus + thickness_bonus
    penalty = (bending_risk*0.35 + shear_risk*0.2 + torsion_risk*0.15 + stress_risk*0.15 + printability_risk*0.15)
    score = _clamp(base - penalty, 0, 100)

    # Determine primary risk
    risks = {"Bending":bending_risk, "Shear":shear_risk, "Torsion":torsion_risk, "Printability":printability_risk}
    primary = max(risks.items(), key=lambda kv: kv[1])[0]
    load_type: LoadType = "Unknown"
    if primary == "Bending": load_type = "Bending"
    elif primary == "Shear": load_type = "Shear"
    elif primary == "Torsion": load_type = "Torsion"
    elif primary == "Printability": load_type = "Multi-axis"

    notes: List[str] = []
    if primary == "Bending":
        notes.append("Moderate bending risk detected.")
    if primary == "Shear":
        notes.append("Shear risk around holes/edges detected.")
    if not has_fillet:
        notes.append("Sharp corners can concentrate stress; consider rounding edges.")
    if overhang > 0.6:
        notes.append("High overhang risk; consider supports or redesign.")

    suggestions: List[StructuralSuggestion] = []
    # Make it stronger suggestions
    if not has_rib:
        suggestions.append(StructuralSuggestion(id="add_rib", label="Add reinforcement rib", action={"type":"toggle_rib","value":True}))
    if not has_fillet:
        suggestions.append(StructuralSuggestion(id="add_fillet", label="Round stress corners (fillet)", action={"type":"toggle_fillet","value":True}))
    if t < 1.15:
        suggestions.append(StructuralSuggestion(id="thicken", label="Increase thickness 12%", action={"type":"thickness","mult":1.12}))

    return StructuralReport(
        confidence=float(round(score, 1)),
        band=_band(score),
        primary_risk=primary,  # type: ignore
        load_type=load_type,
        stress_risk=float(round(stress_risk, 1)),
        printability_risk=float(round(printability_risk, 1)),
        notes=notes,
        suggestions=suggestions,
    )

def apply_strengthen(params: Dict[str, Any]) -> Dict[str, Any]:
    """Apply one best suggestion. Uses neural policy if available, otherwise heuristic."""
    rep = analyze_from_simple_params(params)
    new_params, probs = strengthen_with_policy(params, rep.__dict__)
    if new_params == params and rep.confidence < 70:
        if rep.suggestions:
            act = rep.suggestions[0].action
            t = act.get("type")
            if t == "toggle_rib":
                params["has_rib"] = True
            elif t == "toggle_fillet":
                params["has_fillet"] = True
            elif t == "thickness":
                params["thickness"] = float(params.get("thickness", 1.0)) * float(act.get("mult", 1.12))
            return params
        params["thickness"] = float(params.get("thickness", 1.0)) * 1.05
        return params
    return new_params


# --- Neural policy cache ---
_POLICY: PolicyNet | None = None
_POLICY_IN_DIM: int | None = None

def _policy_base_dir() -> str:
    return os.getenv("EYE_MODELS_DIR", os.path.join(os.path.dirname(__file__), "..", "..", "models"))

def ensure_policy_trained(events_jsonl: str = "events.jsonl") -> None:
    """Train policy if events exist. Called on API startup."""
    global _POLICY, _POLICY_IN_DIM
    # Need in_dim. Build minimal from dummy encode.
    dummy = encode_features({"thickness":1.0,"has_rib":False,"has_fillet":False,"hole_count":0,"cantilever":0,"aspect_ratio":1.0,"overhang_risk":0,"joint_type":"unknown"}, {"load_type":"Unknown","confidence":0,"stress_risk":0,"printability_risk":0})
    _POLICY_IN_DIM = int(dummy.shape[0])
    base = _policy_base_dir()
    model_path = latest_model_path(base)

    # Load if exists
    try:
        from app.services.structural.policy_nn import load_model
        m = load_model(model_path, in_dim=_POLICY_IN_DIM)
        if m is not None:
            _POLICY = m
    except Exception:
        pass

    # Train if events file exists and has rows
    if not os.path.exists(events_jsonl):
        return
    try:
        events = load_events_jsonl(events_jsonl)
        rows = build_training_rows(events)
        if len(rows) < 10:
            return
        model = train_policy(rows, epochs=15, lr=1e-3, hidden=64)
        # versioned save + latest
        vpath = versioned_model_path(base)
        save_model(model, vpath, meta={"rows":len(rows)})
        save_model(model, model_path, meta={"rows":len(rows), "latest":True})
        _POLICY = model
    except Exception:
        return

def strengthen_with_policy(params: Dict[str, Any], report: Dict[str, Any]) -> Tuple[Dict[str, Any], Optional[Dict[str, float]]]:
    global _POLICY, _POLICY_IN_DIM
    if _POLICY is None:
        return params, None
    feats = encode_features(params, report)
    dec = predict_action(_POLICY, feats)
    # Safety: if model suggests no_change but confidence low, allow heuristic to act elsewhere (handled by caller)
    new_params = apply_action(params, dec.action)
    return new_params, dec.probs
