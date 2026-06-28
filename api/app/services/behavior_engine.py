import os, json, time, uuid

DATA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "behavior_engine.json"))

def _load():
    if not os.path.exists(DATA_PATH):
        data = {"temp_sessions": {}, "events": []}
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return data
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def _save(data):
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _event(data, event_type, payload):
    data.setdefault("events", []).insert(0, {
        "id": "evt_" + uuid.uuid4().hex[:10],
        "time": int(time.time()),
        "type": event_type,
        "payload": payload,
    })

def create_temp_session(payload):
    data = _load()
    session_id = "sess_" + uuid.uuid4().hex[:10]
    data.setdefault("temp_sessions", {})[session_id] = {
        "title": payload.get("title") or "Untitled Design",
        "design": payload.get("design") or {},
        "created_at": int(time.time()),
        "expires_at": int(time.time()) + int(payload.get("ttl_seconds", 3600)),
        "recovery_used": False,
        "ghost_saved": False,
    }
    _event(data, "session_created", {"session_id": session_id, "title": payload.get("title")})
    _save(data)
    return {"session_id": session_id, "temp_session": data["temp_sessions"][session_id]}

def ghost_save(payload):
    data = _load()
    session_id = payload.get("session_id")
    session = (data.get("temp_sessions") or {}).get(session_id)
    if not session:
        return {"ok": False, "error": "session_not_found"}
    session["ghost_saved"] = True
    session["ghost_saved_at"] = int(time.time())
    _event(data, "ghost_save", {"session_id": session_id})
    _save(data)
    return {
        "ok": True,
        "session_id": session_id,
        "message": "This is a temporary save. Upgrade to keep your designs forever.",
        "upgrade_required": True,
        "expires_at": session.get("expires_at"),
    }

def exit_warning(payload):
    session_id = payload.get("session_id")
    return {
        "ok": True,
        "session_id": session_id,
        "warning": "Your design will be lost if you leave.",
        "actions": ["save_permanently_pro", "continue_editing", "exit_anyway"],
    }

def recover_session(payload):
    data = _load()
    session_id = payload.get("session_id")
    session = (data.get("temp_sessions") or {}).get(session_id)
    if not session:
        return {"ok": False, "error": "session_not_found"}
    if session.get("recovery_used"):
        return {"ok": False, "error": "recovery_already_used"}
    if int(time.time()) > int(session.get("expires_at", 0)):
        return {"ok": False, "error": "session_expired"}
    session["recovery_used"] = True
    _event(data, "session_recovered", {"session_id": session_id})
    _save(data)
    return {
        "ok": True,
        "message": "We recovered your last design.",
        "session_id": session_id,
        "temp_session": session,
        "actions": ["restore_session", "save_permanently_pro", "discard"],
    }

def record_print_success(payload):
    data = _load()
    rec = {
        "title": payload.get("title") or "Successful Print",
        "message": "You just created something real. Want to create more... or even earn from your designs?",
        "actions": ["continue_creating", "upgrade_to_pro", "learn_how_to_earn"],
        "printed_at": int(time.time()),
        "printer_id": payload.get("printer_id"),
        "rating": payload.get("rating"),
    }
    _event(data, "print_success", rec)
    _save(data)
    return {"ok": True, "success_prompt": rec}

def get_events(limit=100):
    return (_load().get("events") or [])[:limit]
