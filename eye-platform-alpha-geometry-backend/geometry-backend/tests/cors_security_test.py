from fastapi import FastAPI
from fastapi.testclient import TestClient
from pathlib import Path

from app.cors import ALLOWED_HEADERS, ALLOWED_METHODS, install_cors, parse_allowed_origins

PRODUCTION = "https://dragonfly-frontend.onrender.com"
LOCAL = "http://localhost:8081"
STAGING = "https://dragonfly-staging.example.com"


def make_client(origins: list[str]) -> TestClient:
    app = FastAPI()
    install_cors(app, origins)
    app.get("/resource")(lambda: {"ok": True})
    return TestClient(app)


assert parse_allowed_origins(f"{PRODUCTION}, {LOCAL}/, {STAGING}, {PRODUCTION}") == [PRODUCTION, LOCAL, STAGING]
render_config = (Path(__file__).resolve().parents[3] / "render.yaml").read_text(encoding="utf-8")
assert "key: EYE_ALLOWED_ORIGINS" in render_config and f"value: {PRODUCTION}" in render_config
for invalid in ("*", "https://example.com/path", "file://localhost", "https://user@example.com"):
    try:
        parse_allowed_origins(invalid)
    except RuntimeError:
        pass
    else:
        raise AssertionError(f"accepted invalid CORS origin {invalid}")

client = make_client([PRODUCTION, LOCAL, STAGING])
allowed = client.options(
    "/resource",
    headers={
        "Origin": PRODUCTION,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "authorization,content-type,idempotency-key",
    },
)
assert allowed.status_code == 200, allowed.text
assert allowed.headers["access-control-allow-origin"] == PRODUCTION
assert set(ALLOWED_METHODS) == {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"}
assert {header.lower() for header in ALLOWED_HEADERS} == {"authorization", "content-type", "idempotency-key"}
assert set(allowed.headers["access-control-allow-methods"].split(", ")) == set(ALLOWED_METHODS)
returned_headers = {h.lower() for h in allowed.headers["access-control-allow-headers"].split(", ")}
assert {header.lower() for header in ALLOWED_HEADERS} <= returned_headers
assert returned_headers - {header.lower() for header in ALLOWED_HEADERS} <= {"accept", "accept-language", "content-language"}
assert "*" not in allowed.headers["access-control-allow-origin"]

rejected = client.options(
    "/resource",
    headers={
        "Origin": "https://evil.example",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "authorization",
    },
)
assert rejected.status_code == 400, rejected.text
assert "access-control-allow-origin" not in rejected.headers
disallowed_header = client.options(
    "/resource",
    headers={
        "Origin": PRODUCTION,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "x-unapproved",
    },
)
assert disallowed_header.status_code == 400
simple = client.get("/resource", headers={"Origin": "https://evil.example"})
assert simple.status_code == 403
assert "access-control-allow-origin" not in simple.headers
print("CORS security PASS")
