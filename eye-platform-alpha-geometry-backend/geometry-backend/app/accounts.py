from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
import threading
import time
import uuid
from collections import defaultdict, deque
from typing import Optional

from .persistence.repository import DuplicateError, Repository, Row

EMAIL_PATTERN = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,255}\.[^@\s]{2,}$")
MIN_PASSWORD_LENGTH = 10
MAX_PASSWORD_LENGTH = 200
SCRYPT_N, SCRYPT_R, SCRYPT_P = 2**14, 8, 1


class AuthError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=32)
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt, expected = stored.split("$")
        if scheme != "scrypt":
            return False
        digest = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt), n=int(n), r=int(r), p=int(p), dklen=32)
        return hmac.compare_digest(digest, base64.b64decode(expected))
    except (ValueError, TypeError):
        return False


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def public_user(user: Row) -> dict:
    return {"id": user["id"], "email": user["email"], "name": user["display_name"]}


class LoginLimiter:
    """Per-process throttle for failed logins; multi-instance deployments need a shared limiter."""

    def __init__(self, max_failures: int = 5, window_seconds: int = 900):
        self.max_failures = max_failures
        self.window = window_seconds
        self._failures: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> deque:
        bucket = self._failures[key]
        while bucket and bucket[0] < now - self.window:
            bucket.popleft()
        return bucket

    def blocked(self, key: str) -> bool:
        with self._lock:
            return len(self._prune(key, time.time())) >= self.max_failures

    def record_failure(self, key: str) -> None:
        with self._lock:
            self._prune(key, time.time()).append(time.time())

    def clear(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)


class AuthService:
    def __init__(self, repo: Repository, session_ttl_seconds: int):
        self.repo = repo
        self.session_ttl = session_ttl_seconds
        self.limiter = LoginLimiter()
        self._dummy_hash = hash_password(secrets.token_urlsafe(12))

    def _open_session(self, user: Row) -> dict:
        token = secrets.token_urlsafe(32)
        now = time.time()
        expires_at = now + self.session_ttl
        self.repo.create_session(uuid.uuid4().hex, user["id"], _token_hash(token), now, expires_at)
        return {"token": token, "expires_at": expires_at, "user": public_user(user)}

    def signup(self, email: str, password: str, name: str = "") -> dict:
        email = (email or "").strip().lower()
        if not EMAIL_PATTERN.match(email):
            raise AuthError("Enter a valid email address.")
        if not MIN_PASSWORD_LENGTH <= len(password or "") <= MAX_PASSWORD_LENGTH:
            raise AuthError(f"Use a password between {MIN_PASSWORD_LENGTH} and {MAX_PASSWORD_LENGTH} characters.")
        try:
            user = self.repo.create_user(uuid.uuid4().hex, email, hash_password(password), (name or "").strip()[:80], time.time())
        except DuplicateError:
            raise AuthError("An account with this email already exists.", 409) from None
        return self._open_session(user)

    def login(self, email: str, password: str) -> dict:
        email = (email or "").strip().lower()
        if self.limiter.blocked(email):
            raise AuthError("Too many failed attempts. Try again later.", 429)
        user = self.repo.get_user_by_email(email)
        valid = verify_password(password or "", user["password_hash"] if user else self._dummy_hash)
        if not user or not valid or user["disabled"]:
            self.limiter.record_failure(email)
            raise AuthError("Email or password is incorrect.", 401)
        self.limiter.clear(email)
        return self._open_session(user)

    def authenticate(self, token: Optional[str]) -> Optional[tuple[Row, Row]]:
        if not token:
            return None
        session = self.repo.get_session_by_token_hash(_token_hash(token))
        now = time.time()
        if not session or session["revoked_at"] is not None or session["expires_at"] <= now:
            return None
        user = self.repo.get_user(session["user_id"])
        if not user or user["disabled"]:
            return None
        self.repo.touch_session(session["id"], now)
        return user, session

    def logout(self, session: Row) -> None:
        self.repo.revoke_session(session["id"], time.time())
