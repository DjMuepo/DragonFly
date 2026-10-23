from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.accounts import LoginLimiter
from app.cors import install_cors, parse_allowed_origins
from app.persistence.settings import StorageSettings
from app.request_limits import RequestSizeLimitMiddleware
from app.runtime import migrate_legacy_storage

PRODUCTION = "https://dragonfly-frontend.onrender.com"
assert parse_allowed_origins("") == []

limiter = LoginLimiter(max_failures=5)
for _ in range(5):
    limiter.record_failure("user@example.com", "203.0.113.4")
assert limiter.blocked("user@example.com", "203.0.113.4")
assert not limiter.blocked("user@example.com", "203.0.113.5")
limiter.clear("user@example.com", "203.0.113.4")
assert not limiter.blocked("user@example.com", "203.0.113.4")
for index in range(20):
    limiter.record_failure(f"other{index}@example.com", "203.0.113.4")
assert limiter.blocked("different@example.com", "203.0.113.4")

app = FastAPI()
app.add_middleware(RequestSizeLimitMiddleware, upload_max_bytes=1024)
install_cors(app, [PRODUCTION])

@app.post("/v1/auth/login")
async def read_body(request: Request):
    return {"length": len(await request.body())}

client = TestClient(app)
assert client.post("/v1/auth/login", content=b"x" * 1024).status_code == 200
assert client.post("/v1/auth/login", content=b"x" * (64 * 1024 + 1)).status_code == 413
assert client.post("/v1/geometry/generate-from-image", content=b"x" * 1025).status_code == 413

root = Path(__file__).resolve().parents[1]
env = dict(os.environ)
for key in ("EYE_DATA_DIR", "EYE_STORAGE_DURABLE", "EYE_SIGNING_SECRET"):
    env.pop(key, None)
env["EYE_REQUIRE_DURABLE_STORAGE"] = "1"
env["PYTHONPATH"] = str(root)
with tempfile.TemporaryDirectory(prefix="dragonfly-required-storage-") as temp:
    env["EYE_DATA_DIR"] = str(Path(temp) / "ephemeral")
    env["EYE_STORAGE_DURABLE"] = "0"
    result = subprocess.run([sys.executable, "-c", "from app.runtime import build_runtime; build_runtime()"], cwd=root, env=env, capture_output=True, text=True)
    assert result.returncode != 0 and "not configured" in result.stderr

with tempfile.TemporaryDirectory(prefix="dragonfly-required-secret-") as temp:
    env["EYE_DATA_DIR"] = str(Path(temp) / "disk")
    env["EYE_STORAGE_DURABLE"] = "1"
    env.pop("EYE_SIGNING_SECRET", None)
    result = subprocess.run([sys.executable, "-c", "from app.runtime import build_runtime; build_runtime()"], cwd=root, env=env, capture_output=True, text=True)
    assert result.returncode != 0 and "stable EYE_SIGNING_SECRET" in result.stderr

with tempfile.TemporaryDirectory(prefix="dragonfly-required-backup-") as temp:
    env["EYE_DATA_DIR"] = str(Path(temp) / "disk")
    env["EYE_STORAGE_DURABLE"] = "1"
    env["EYE_SIGNING_SECRET"] = "test-signing-secret"
    env["EYE_REQUIRE_BACKUP"] = "1"
    env["EYE_BACKUP_DIR"] = str(Path(temp) / "backup")
    env.pop("EYE_BACKUP_EXTERNAL", None)
    env.pop("EYE_BACKUP_RESTORE_TESTED", None)
    result = subprocess.run([sys.executable, "-c", "from app.runtime import build_runtime; build_runtime()"], cwd=root, env=env, capture_output=True, text=True)
    assert result.returncode != 0 and "requires an external EYE_BACKUP_DIR" in result.stderr

with tempfile.TemporaryDirectory(prefix="dragonfly-corrupt-database-") as temp:
    env["EYE_DATA_DIR"] = str(Path(temp) / "disk")
    env.pop("EYE_REQUIRE_BACKUP", None)
    env.pop("EYE_BACKUP_DIR", None)
    database = Path(env["EYE_DATA_DIR"]) / "dragonfly.db"
    database.parent.mkdir(parents=True)
    database.write_bytes(b"not a sqlite database")
    result = subprocess.run([sys.executable, "-c", "import app.runtime as r; r.migrate_legacy_storage=lambda settings: {}; r.build_runtime()"], cwd=root, env=env, capture_output=True, text=True)
    assert result.returncode != 0 and ("integrity check failed" in result.stderr or "file is not a database" in result.stderr)

with tempfile.TemporaryDirectory(prefix="dragonfly-legacy-migration-") as temp:
    base = Path(temp)
    legacy = base / "legacy"
    data = base / "persistent"
    (legacy / "data").mkdir(parents=True)
    (legacy / "static/models").mkdir(parents=True)
    (legacy / "static/uploads").mkdir(parents=True)
    (legacy / "data/sources").mkdir(parents=True)
    (legacy / "static/models/old.glb").write_bytes(b"old glb")
    (legacy / "static/uploads/transient.jpg").write_bytes(b"temporary")
    (legacy / "data/sources/photo.jpg").write_bytes(b"source")
    import sqlite3
    legacy_db = sqlite3.connect(legacy / "data/dragonfly.db")
    legacy_db.execute("CREATE TABLE preserved (value TEXT)")
    legacy_db.execute("INSERT INTO preserved VALUES ('kept')")
    legacy_db.commit()
    legacy_db.close()
    settings = StorageSettings(data, data / "models", data / "uploads", data / "sources", data / "dragonfly.db", True, 1000, 900, b"secret", True, True, 1, 1, 1, 1, 1024, 600, 60, None, False, False, False)
    copied = migrate_legacy_storage(settings, legacy)
    assert copied["database_copied"] and copied["copied_files"] == 3
    assert (data / "models/old.glb").read_bytes() == b"old glb"
    restored_db = sqlite3.connect(data / "dragonfly.db")
    assert restored_db.execute("SELECT value FROM preserved").fetchone()[0] == "kept"
    restored_db.close()
    (legacy / "static/models/old.glb").write_bytes(b"different legacy bytes")
    try:
        migrate_legacy_storage(settings, legacy)
    except RuntimeError as error:
        assert "conflicts with persistent storage" in str(error)
    else:
        raise AssertionError("conflicting legacy model should block startup")
    assert (data / "models/old.glb").read_bytes() == b"old glb"
print("security stabilization PASS")
