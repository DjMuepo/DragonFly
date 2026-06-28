from __future__ import annotations
import os
from typing import Any, Dict, List, Optional

DATABASE_URL = os.environ.get("DATABASE_URL", "")

class PostgresNotConfigured(RuntimeError):
    pass

def _ensure_configured() -> None:
    if not DATABASE_URL:
        raise PostgresNotConfigured("DATABASE_URL not configured")

def healthcheck() -> Dict[str, Any]:
    return {"ok": bool(DATABASE_URL), "configured": bool(DATABASE_URL), "mode": "postgres"}

def create_user(user: Dict[str, Any]) -> Dict[str, Any]:
    _ensure_configured()
    return user

def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    _ensure_configured()
    return None

def create_session(token: str, user_id: str) -> None:
    _ensure_configured()

def get_user_by_token(token: str) -> Optional[Dict[str, Any]]:
    _ensure_configured()
    return None

def insert_design(design: Dict[str, Any]) -> Dict[str, Any]:
    _ensure_configured()
    return design

def list_public_designs() -> List[Dict[str, Any]]:
    _ensure_configured()
    return []

def get_design(slug: str) -> Optional[Dict[str, Any]]:
    _ensure_configured()
    return None
