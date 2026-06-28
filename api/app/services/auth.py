from __future__ import annotations
from typing import Dict, Any, Optional
from .storage import load_db, save_db, new_id, now_ts
from app.security.auth_utils import hash_password, verify_password, validate_password_strength, normalize_email
from app.security.rate_limit import check_and_increment

def signup(email: str, password: str, name: str = "", interests=None, skill_level: str = "beginner") -> Dict[str, Any]:
    db = load_db()
    email_l = normalize_email(email)
    rl = check_and_increment(f"signup:{email_l}", limit=8, window_seconds=3600)
    if not rl["allowed"]:
        raise ValueError("rate_limited")
    if any(u["email"] == email_l for u in db["users"]):
        raise ValueError("email_exists")
    pw = validate_password_strength(password)
    if not pw["ok"]:
        raise ValueError("weak_password:" + ",".join(pw["reasons"]))
    user = {
        "id": new_id("usr"),
        "email": email_l,
        "password": hash_password(password),
        "name": name.strip() or "User",
        "interests": interests or [],
        "skill_level": skill_level or "beginner",
        "created_at": now_ts(),
    }
    db["users"].append(user)
    token = new_id("sess")
    db["sessions"].append({"token": token, "user_id": user["id"], "created_at": now_ts()})
    save_db(db)
    return {"token": token, "user": {k: v for k, v in user.items() if k != "password"}}

def login(email: str, password: str) -> Dict[str, Any]:
    db = load_db()
    email_l = normalize_email(email)
    rl = check_and_increment(f"login:{email_l}", limit=12, window_seconds=900)
    if not rl["allowed"]:
        raise ValueError("rate_limited")
    user = next((u for u in db["users"] if u["email"] == email_l), None)
    if not user or not verify_password(password, user.get("password","")):
        raise ValueError("invalid_credentials")
    token = new_id("sess")
    db["sessions"].append({"token": token, "user_id": user["id"], "created_at": now_ts()})
    save_db(db)
    return {"token": token, "user": {k: v for k, v in user.items() if k != "password"}}

def get_user_by_token(token: str) -> Optional[Dict[str, Any]]:
    db = load_db()
    sess = next((s for s in db["sessions"] if s["token"] == token), None)
    if not sess:
        return None
    user = next((u for u in db["users"] if u["id"] == sess["user_id"]), None)
    if not user:
        return None
    return {k: v for k, v in user.items() if k != "password"}

def list_user_designs(user_id: str):
    db = load_db()
    return [d for d in db["designs"] if d.get("owner_id") == user_id]
