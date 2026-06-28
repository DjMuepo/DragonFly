import os, json, time

DATA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "feature_access.json"))

DEFAULT_DATA = {
    "features": {
        "scan_world": {"enabled": True, "default_tier": "pro", "description": "Live scan-the-world workflow"},
        "autosave_object_dna": {"enabled": True, "default_tier": "pro", "description": "Automatic persistent Object DNA save"},
        "ar_placement": {"enabled": True, "default_tier": "free", "description": "AR placement planning"},
        "collaborative_scanning": {"enabled": True, "default_tier": "pro", "description": "Multi-user collaborative scan"},
        "world_map_publish": {"enabled": True, "default_tier": "pro", "description": "Publish object to world map"},
        "fix_object": {"enabled": True, "default_tier": "free", "description": "Repair workflow"},
        "learning_summary": {"enabled": True, "default_tier": "pro", "description": "AI learning recommendations"},
        "challenge_rewards": {"enabled": False, "default_tier": "pro", "description": "XP / badges / rewards"}
    },
    "user_overrides": {},
    "audit_log": []
}

TIER_ORDER = {"free": 0, "pro": 1, "enterprise": 2, "admin": 3}

def _load():
    if not os.path.exists(DATA_PATH):
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_DATA, f, ensure_ascii=False, indent=2)
        return json.loads(json.dumps(DEFAULT_DATA))
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def _save(data):
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def list_features():
    return _load()

def _tier_allows(user_tier, required_tier):
    return TIER_ORDER.get(user_tier or "free", 0) >= TIER_ORDER.get(required_tier or "free", 0)

def check_access(payload):
    data = _load()
    feature_key = payload.get("feature_key")
    user_tier = payload.get("user_tier") or "free"
    user_id = payload.get("user_id") or ""
    is_admin = bool(payload.get("is_admin", False))
    feature = (data.get("features") or {}).get(feature_key)
    if not feature:
        return {"ok": False, "allowed": False, "error": "feature_not_found"}
    if is_admin:
        return {"ok": True, "allowed": True, "reason": "admin_override", "feature": feature}
    if not feature.get("enabled", False):
        return {"ok": True, "allowed": False, "reason": "feature_disabled", "feature": feature}
    override = ((data.get("user_overrides") or {}).get(user_id) or {}).get(feature_key)
    if override:
        forced = override.get("forced_access")
        if forced == "allow":
            return {"ok": True, "allowed": True, "reason": "user_override_allow", "feature": feature, "override": override}
        if forced == "deny":
            return {"ok": True, "allowed": False, "reason": "user_override_deny", "feature": feature, "override": override}
    required_tier = feature.get("default_tier") or "free"
    allowed = _tier_allows(user_tier, required_tier)
    return {"ok": True, "allowed": allowed, "reason": "tier_match" if allowed else "tier_upgrade_required", "required_tier": required_tier, "feature": feature}

def update_feature(payload):
    data = _load()
    feature_key = payload.get("feature_key")
    actor = payload.get("actor") or "admin"
    feature = (data.setdefault("features", {})).get(feature_key)
    if not feature:
        return {"ok": False, "error": "feature_not_found"}
    before = dict(feature)
    if "enabled" in payload:
        feature["enabled"] = bool(payload["enabled"])
    if "default_tier" in payload and payload["default_tier"] in TIER_ORDER:
        feature["default_tier"] = payload["default_tier"]
    if "description" in payload:
        feature["description"] = payload["description"]
    data.setdefault("audit_log", []).insert(0, {"time": int(time.time()), "actor": actor, "type": "feature_update", "feature_key": feature_key, "before": before, "after": dict(feature)})
    _save(data)
    return {"ok": True, "feature_key": feature_key, "feature": feature}

def set_user_override(payload):
    data = _load()
    feature_key = payload.get("feature_key")
    user_id = payload.get("user_id")
    forced_access = payload.get("forced_access")
    actor = payload.get("actor") or "admin"
    if feature_key not in (data.get("features") or {}):
        return {"ok": False, "error": "feature_not_found"}
    if forced_access not in ("allow", "deny", "clear"):
        return {"ok": False, "error": "invalid_forced_access"}
    if not user_id:
        return {"ok": False, "error": "missing_user_id"}
    target = (data.setdefault("user_overrides", {})).setdefault(user_id, {})
    before = dict(target.get(feature_key) or {})
    if forced_access == "clear":
        if feature_key in target:
            del target[feature_key]
        after = None
    else:
        target[feature_key] = {"forced_access": forced_access, "updated_at": int(time.time())}
        after = dict(target[feature_key])
    data.setdefault("audit_log", []).insert(0, {"time": int(time.time()), "actor": actor, "type": "user_override", "feature_key": feature_key, "user_id": user_id, "before": before, "after": after})
    _save(data)
    return {"ok": True, "user_id": user_id, "feature_key": feature_key, "override": after}

def get_audit_log(limit=100):
    return (_load().get("audit_log") or [])[:limit]
