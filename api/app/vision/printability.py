from __future__ import annotations
from typing import Dict, Any, List

def analyze_printability(parametric: Dict[str, Any]) -> Dict[str, Any]:
    family = (parametric.get("family") or "object").lower()
    params = dict(parametric.get("params") or {})
    notes: List[str] = []
    suggestions: List[str] = []
    risks: List[str] = []
    score = 92
    thickness = float(params.get("thickness", params.get("wall_thickness", 0.12)) or 0.12)
    aspect_ratio = float(parametric.get("aspect_ratio", 1.0) or 1.0)
    depth_ratio = float(parametric.get("estimated_depth_ratio", 0.2) or 0.2)
    has_fillet = bool(params.get("has_fillet", False))
    has_rib = bool(params.get("has_rib", False))
    hole_count = int(params.get("hole_count", params.get("mount_holes", 0)) or 0)
    cantilever = float(params.get("cantilever", 0.0) or 0.0)

    if thickness < 0.1:
        score -= 22; risks.append("thin_walls"); suggestions.append("Increase wall thickness")
    elif thickness < 0.16:
        score -= 10; risks.append("light_walls"); suggestions.append("Slightly increase wall thickness")
    if aspect_ratio > 1.7:
        score -= 8; risks.append("slender_geometry"); suggestions.append("Shorten unsupported span or add support ribs")
    if cantilever > 0.35:
        score -= 12; risks.append("cantilever_risk"); suggestions.append("Reduce unsupported cantilever or add reinforcement")
    if family in ("hook", "bracket", "clip") and not has_rib:
        score -= 7; notes.append("Structural family without reinforcement rib"); suggestions.append("Add reinforcement rib")
    if family in ("hook", "clip") and not has_fillet:
        score -= 6; notes.append("Sharp transition may concentrate stress"); suggestions.append("Add fillet to smooth corners")
    if family == "enclosure" and thickness < 0.12:
        score -= 8; suggestions.append("Increase enclosure wall thickness")
    if hole_count > 0 and thickness < 0.14:
        score -= 6; notes.append("Mount holes with low thickness can weaken the part"); suggestions.append("Thicken area around holes")
    if depth_ratio < 0.12 and family in ("bracket","hook","clip"):
        score -= 5; suggestions.append("Increase depth for better rigidity")

    score = max(35, min(98, int(score)))
    band = "HIGH" if score >= 85 else "MEDIUM" if score >= 65 else "LOW"
    if not suggestions:
        suggestions.append("Looks printable with standard PLA settings")
    checks = {
        "thin_walls": thickness >= 0.1,
        "overhang_risk": cantilever <= 0.35,
        "stress_transitions": has_fillet or family not in ("hook","clip"),
        "reinforcement": has_rib or family not in ("hook","bracket","clip"),
    }
    return {"family": family, "print_confidence": score, "band": band, "risks": risks, "notes": notes, "suggestions": suggestions[:4], "checks": checks, "recommended_material": "PLA" if family not in ("clip","hook","bracket") else "PETG"}
