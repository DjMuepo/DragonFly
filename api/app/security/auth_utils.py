from __future__ import annotations
import base64, hashlib, hmac, os
from typing import Dict

_ITERATIONS = 120000

def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    return f"pbkdf2_sha256${_ITERATIONS}$" + base64.b64encode(salt).decode("ascii") + "$" + base64.b64encode(dk).decode("ascii")

def verify_password(password: str, encoded: str) -> bool:
    try:
        algo, iterations_s, salt_b64, hash_b64 = encoded.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        salt = base64.b64decode(salt_b64.encode("ascii"))
        expected = base64.b64decode(hash_b64.encode("ascii"))
        test = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations_s))
        return hmac.compare_digest(expected, test)
    except Exception:
        return False

def validate_password_strength(password: str) -> Dict[str, object]:
    reasons = []
    if len(password) < 8: reasons.append("at least 8 characters")
    if password.lower() == password: reasons.append("one uppercase letter")
    if password.upper() == password: reasons.append("one lowercase letter")
    if not any(ch.isdigit() for ch in password): reasons.append("one number")
    return {"ok": len(reasons) == 0, "reasons": reasons}

def normalize_email(email: str) -> str:
    return (email or "").strip().lower()
