import os, json, time, random, string

DATA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "invite_registry.json"))

def _load():
    if not os.path.exists(DATA_PATH):
        data = {"codes": {}, "redemptions": []}
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return data
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def _save(data):
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _make_code():
    return "MUEPO-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))

def create_invite(payload):
    data = _load()
    code = payload.get("code") or _make_code()
    data["codes"][code] = {
        "enabled": True,
        "created_at": int(time.time()),
        "created_by": payload.get("created_by") or "owner_admin",
        "usage_limit": int(payload.get("usage_limit", 1)),
        "uses": 0,
        "assigned_email": payload.get("assigned_email"),
        "expires_at": payload.get("expires_at"),
    }
    _save(data)
    return {"ok": True, "code": code, "invite": data["codes"][code]}

def validate_invite(payload):
    data = _load()
    code = payload.get("code")
    invite = (data.get("codes") or {}).get(code)
    if not invite:
        return {"ok": False, "valid": False, "error": "not_found"}
    if not invite.get("enabled", False):
        return {"ok": False, "valid": False, "error": "disabled"}
    if invite.get("expires_at") and int(time.time()) > int(invite["expires_at"]):
        return {"ok": False, "valid": False, "error": "expired"}
    if int(invite.get("uses", 0)) >= int(invite.get("usage_limit", 1)):
        return {"ok": False, "valid": False, "error": "usage_limit_reached"}
    assigned = invite.get("assigned_email")
    email = payload.get("email")
    if assigned and email and assigned.lower() != email.lower():
        return {"ok": False, "valid": False, "error": "email_mismatch"}
    return {"ok": True, "valid": True, "invite": invite}

def redeem_invite(payload):
    data = _load()
    code = payload.get("code")
    invite = (data.get("codes") or {}).get(code)
    if not invite:
        return {"ok": False, "redeemed": False, "error": "not_found"}
    check = validate_invite(payload)
    if not check.get("valid"):
        return {"ok": False, "redeemed": False, "error": check.get("error")}
    invite["uses"] = int(invite.get("uses", 0)) + 1
    data.setdefault("redemptions", []).insert(0, {
        "time": int(time.time()),
        "code": code,
        "email": payload.get("email"),
        "user_id": payload.get("user_id"),
    })
    _save(data)
    return {"ok": True, "redeemed": True, "code": code, "invite": invite}

def disable_invite(payload):
    data = _load()
    code = payload.get("code")
    invite = (data.get("codes") or {}).get(code)
    if not invite:
        return {"ok": False, "error": "not_found"}
    invite["enabled"] = False
    _save(data)
    return {"ok": True, "code": code, "invite": invite}

def list_invites():
    return _load()
