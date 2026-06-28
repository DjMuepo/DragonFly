from __future__ import annotations
from typing import Dict, Any
from .feature_store import load_features

def get_family_defaults(family: str) -> Dict[str, Any]:
    features = load_features()
    fam = (features.get("families") or {}).get((family or "").lower(), {})
    return {
        "min_thickness": fam.get("min_thickness"),
        "preferred_material": fam.get("preferred_material", "PLA"),
        "reinforcement_bias": fam.get("reinforcement_bias", 0.0),
        "fillet_bias": fam.get("fillet_bias", 0.0),
        "sample_weight": fam.get("sample_weight", 0.0),
    }

def adapt_parametric_draft(parametric: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(parametric)
    params = dict(out.get("params") or {})
    family = (out.get("family") or "").lower()
    defaults = get_family_defaults(family)

    min_thickness = defaults.get("min_thickness")
    if min_thickness is not None:
        current = float(params.get("thickness", params.get("wall_thickness", 0.12)) or 0.12)
        if current < float(min_thickness):
            if "wall_thickness" in params:
                params["wall_thickness"] = round(float(min_thickness), 4)
            else:
                params["thickness"] = round(float(min_thickness), 4)

    if defaults.get("reinforcement_bias", 0) > 0.12:
        params["has_rib"] = True
    if defaults.get("fillet_bias", 0) > 0.1:
        params["has_fillet"] = True

    out["params"] = params
    out["learned_defaults"] = defaults
    return out
