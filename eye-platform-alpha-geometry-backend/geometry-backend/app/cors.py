from __future__ import annotations

import os
from urllib.parse import urlsplit

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

ALLOWED_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
ALLOWED_HEADERS = ["Authorization", "Content-Type", "Idempotency-Key"]


class OriginGuardMiddleware:
    def __init__(self, app, allowed_origins: list[str]):
        self.app = app
        self.allowed_origins = set(allowed_origins)

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            origin = headers.get(b"origin", b"").decode("latin-1")
            if origin and origin not in self.allowed_origins:
                response = JSONResponse({"detail": "Origin is not allowed."}, status_code=403)
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


def parse_allowed_origins(value: str | None = None) -> list[str]:
    configured = os.environ.get("EYE_ALLOWED_ORIGINS", "") if value is None else value
    origins: list[str] = []
    for raw in configured.split(","):
        origin = raw.strip().rstrip("/")
        if not origin:
            continue
        parsed = urlsplit(origin)
        if parsed.scheme not in {"https", "http"} or not parsed.netloc or parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.password:
            raise RuntimeError(f"Invalid EYE_ALLOWED_ORIGINS entry: {raw.strip()!r}")
        if origin == "*":
            raise RuntimeError("Wildcard origins are not allowed in EYE_ALLOWED_ORIGINS.")
        origins.append(origin)
    return list(dict.fromkeys(origins))


def install_cors(app: FastAPI, allowed_origins: list[str] | None = None) -> list[str]:
    origins = parse_allowed_origins() if allowed_origins is None else allowed_origins
    app.add_middleware(OriginGuardMiddleware, allowed_origins=origins)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=ALLOWED_METHODS,
        allow_headers=ALLOWED_HEADERS,
        max_age=600,
    )
    return origins
