"""Controlled paid-prediction gate tests. All inference is mocked; no network calls or paid predictions.

Run: PYTHONPATH=. python tests/paid_test_gate_test.py
"""
from __future__ import annotations

import io
import json
import os
import tempfile
import threading
import urllib.request
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("EYE_RECONSTRUCTION_DEBUG", "0")

from PIL import Image

from app.durable_jobs import DurableJobs
from app.environment import controlled_paid_test_allowed
from app.paid_test_gate import (
    PaidPredictionGate,
    PaidTestGateError,
    register_gate,
    reserve_before_submission,
    validate_paid_test_settings,
)
from app.persistence.repository import QuotaExceeded
from app.persistence.sqlite_repository import SqliteRepository
from app.providers import ReconstructionRequest, ReplicateGPUProvider, USER_AGENT

STAGING_SERVICE = {"EYE_APP_ENV": "staging", "RENDER": "true", "RENDER_SERVICE_NAME": "dragonfly-staging-geometry-backend"}
AUTHORIZED = "pilot@example.com"
GATE_ON = {"EYE_PAID_TEST_MODE": "1", "EYE_PAID_TEST_AUTHORIZED_USER_EMAIL": AUTHORIZED, "EYE_PAID_TEST_GLOBAL_LIMIT": "1"}


def expect_raises(exc_type, fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
    except exc_type as error:
        return error
    raise AssertionError(f"expected {exc_type.__name__} from {fn}")


# --- Part A1: startup validation fails closed outside staging/test ------------------------------
with patch.dict(os.environ, {"EYE_APP_ENV": "production", "RENDER": "true", "RENDER_SERVICE_NAME": "dragonfly-production-backend", **GATE_ON}):
    assert not controlled_paid_test_allowed()
    expect_raises(RuntimeError, validate_paid_test_settings)

with patch.dict(os.environ, {**STAGING_SERVICE, "RENDER_SERVICE_NAME": "some-other-service", **GATE_ON}):
    expect_raises(RuntimeError, validate_paid_test_settings)

with patch.dict(os.environ, {**STAGING_SERVICE, **GATE_ON}):
    assert controlled_paid_test_allowed()
    validate_paid_test_settings()

# The paid provider on staging requires the gate to be configured.
with patch.dict(os.environ, {**STAGING_SERVICE, "EYE_RECONSTRUCTION_PROVIDER": "replicate"}):
    expect_raises(RuntimeError, validate_paid_test_settings)
with patch.dict(os.environ, {**STAGING_SERVICE, "EYE_RECONSTRUCTION_PROVIDER": "replicate", **GATE_ON}):
    validate_paid_test_settings()

# Missing/invalid authorized account or limit fails closed.
with patch.dict(os.environ, {**STAGING_SERVICE, **GATE_ON, "EYE_PAID_TEST_AUTHORIZED_USER_EMAIL": ""}):
    expect_raises(RuntimeError, validate_paid_test_settings)
with patch.dict(os.environ, {**STAGING_SERVICE, **GATE_ON, "EYE_PAID_TEST_GLOBAL_LIMIT": "1000"}):
    expect_raises(RuntimeError, validate_paid_test_settings)
with patch.dict(os.environ, {**STAGING_SERVICE, **GATE_ON, "EYE_PAID_TEST_GLOBAL_LIMIT": "one"}):
    expect_raises(RuntimeError, validate_paid_test_settings)
print("startup validation PASS")


def fresh_repo(root: Path) -> SqliteRepository:
    repo = SqliteRepository(root / "gate.db")
    repo.migrate()
    return repo


# --- Part A2: request authorization (guest / unauthorized / authorized / exhausted) -------------
with tempfile.TemporaryDirectory(prefix="dragonfly-gate-") as temp, patch.dict(os.environ, {"EYE_APP_ENV": "test", **GATE_ON}):
    repo = fresh_repo(Path(temp))
    gate = PaidPredictionGate(repo)
    pilot = repo.create_user("u-pilot", AUTHORIZED, "x", "Pilot", 0.0)
    intruder = repo.create_user("u-intruder", "intruder@example.com", "x", "Intruder", 0.0)

    error = expect_raises(PaidTestGateError, gate.authorize_request, None)
    assert error.status_code == 403 and error.code == "paid_test_guest_forbidden"
    error = expect_raises(PaidTestGateError, gate.authorize_request, intruder)
    assert error.status_code == 403 and error.code == "paid_test_unauthorized_user"
    gate.authorize_request(pilot)  # authorized account passes while allowance remains

    # Atomic reservation requires a job owned by the authorized account.
    jobs = DurableJobs(repo)
    pilot_job, _ = jobs.create("generate", pilot["id"], "replicate-remote-gpu", "ai")
    guest_job, _ = jobs.create("generate", None, "replicate-remote-gpu", "ai")
    expect_raises(PaidTestGateError, gate.reserve, None)
    expect_raises(PaidTestGateError, gate.reserve, guest_job["job_id"])
    assert repo.count_paid_predictions() == 0

    reservation = gate.reserve(pilot_job["job_id"])
    assert repo.count_paid_predictions() == 1
    gate.record_submission(reservation, "pred-123", "owner/model:test-version")
    ledger = repo.list_paid_predictions()
    assert ledger[0]["status"] == "submitted" and ledger[0]["prediction_id"] == "pred-123"

    # Exhausted: second reservation and new authorizations are rejected; nothing is restored.
    expect_raises(QuotaExceeded, gate.reserve, pilot_job["job_id"])
    error = expect_raises(PaidTestGateError, gate.authorize_request, pilot)
    assert error.status_code == 429 and error.code == "paid_test_allowance_exhausted"
    assert repo.count_paid_predictions() == 1

    # Persistence across restart: a brand-new repository on the same database stays exhausted.
    restarted = SqliteRepository(Path(temp) / "gate.db")
    assert restarted.count_paid_predictions() == 1
    expect_raises(QuotaExceeded, PaidPredictionGate(restarted).reserve, pilot_job["job_id"])

    status = gate.status()
    assert status == {"enabled": True, "environment_allowed": True, "global_limit": 1, "consumed": 1, "remaining": 0, "authorized_user_configured": True}
print("authorization and persistence PASS")

# --- Part A3: concurrent reservations — exactly one wins ----------------------------------------
with tempfile.TemporaryDirectory(prefix="dragonfly-gate-") as temp, patch.dict(os.environ, {"EYE_APP_ENV": "test", **GATE_ON}):
    repo = fresh_repo(Path(temp))
    results: list[bool] = []
    lock = threading.Lock()

    def try_reserve(index: int) -> None:
        try:
            repo.reserve_paid_prediction(f"r{index}", "u", "j", 1, 0.0)
            won = True
        except QuotaExceeded:
            won = False
        with lock:
            results.append(won)

    threads = [threading.Thread(target=try_reserve, args=(i,)) for i in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert results.count(True) == 1 and repo.count_paid_predictions() == 1, results
print("concurrent reservation PASS")

# --- Part A4: provider integration with mocked transport ----------------------------------------
PROVIDER_ENV = {
    "EYE_APP_ENV": "test",
    **GATE_ON,
    "REPLICATE_API_TOKEN": "test-only",
    "EYE_REPLICATE_MODEL_VERSION": "owner/model:test-version",
    "EYE_RECONSTRUCTION_DEBUG": "0",
}


def make_image(root: Path) -> Path:
    image_path = root / "bottle.jpg"
    Image.new("RGB", (32, 32), "white").save(image_path)
    return image_path


with tempfile.TemporaryDirectory(prefix="dragonfly-gate-") as temp, patch.dict(os.environ, PROVIDER_ENV):
    root = Path(temp)
    repo = fresh_repo(root)
    gate = PaidPredictionGate(repo)
    register_gate(gate)
    pilot = repo.create_user("u-pilot", AUTHORIZED, "x", "Pilot", 0.0)
    jobs = DurableJobs(repo)

    # Mode enabled without an initialized gate fails closed before any submission.
    register_gate(None)
    expect_raises(RuntimeError, reserve_before_submission, "any-job")
    register_gate(gate)

    # Ambiguous network failure on the prediction POST: the reservation stays consumed
    # and the provider makes exactly one submission attempt (no automatic retry).
    post_attempts: list[str] = []

    def ambiguous_transport(method, path, token, body, absolute=False):
        if method == "POST" and path == "/predictions":
            post_attempts.append(path)
            raise OSError("connection reset during submission")
        raise AssertionError(f"unexpected transport call: {method} {path}")

    job, _ = jobs.create("generate", pilot["id"], "replicate-remote-gpu", "ai")
    request = ReconstructionRequest(label="bottle", confidence=0.9, image_path=make_image(root), job_id=job["job_id"])
    with patch.object(ReplicateGPUProvider, "_request", staticmethod(ambiguous_transport)):
        expect_raises(OSError, ReplicateGPUProvider().generate, request, root)
    assert post_attempts == ["/predictions"]
    assert repo.count_paid_predictions() == 1
    assert repo.list_paid_predictions()[0]["status"] == "reserved"  # consumed, never auto-restored

    # Exhausted allowance: the provider refuses before any network submission.
    def forbidden_transport(method, path, token, body, absolute=False):
        raise AssertionError("no transport call is allowed once the allowance is exhausted")

    with patch.object(ReplicateGPUProvider, "_request", staticmethod(forbidden_transport)):
        expect_raises(QuotaExceeded, ReplicateGPUProvider().generate, request, root)
    assert repo.count_paid_predictions() == 1
    register_gate(None)

with tempfile.TemporaryDirectory(prefix="dragonfly-gate-") as temp, patch.dict(os.environ, PROVIDER_ENV):
    # Submission accepted remotely: the prediction id is recorded on the consumed reservation.
    root = Path(temp)
    repo = fresh_repo(root)
    register_gate(PaidPredictionGate(repo))
    pilot = repo.create_user("u-pilot", AUTHORIZED, "x", "Pilot", 0.0)
    job, _ = DurableJobs(repo).create("generate", pilot["id"], "replicate-remote-gpu", "ai")

    def failing_prediction_transport(method, path, token, body, absolute=False):
        if method == "POST" and path == "/predictions":
            return {"id": "controlled-1", "status": "processing", "urls": {"get": "https://api.replicate.com/v1/predictions/controlled-1"}}
        if method == "GET":
            return {"id": "controlled-1", "status": "failed", "error": "mock remote failure"}
        raise AssertionError(f"unexpected transport call: {method} {path}")

    request = ReconstructionRequest(label="bottle", confidence=0.9, image_path=make_image(root), job_id=job["job_id"])
    with patch.object(ReplicateGPUProvider, "_request", staticmethod(failing_prediction_transport)):
        error = expect_raises(RuntimeError, ReplicateGPUProvider().generate, request, root)
    assert "mock remote failure" in str(error)
    ledger = repo.list_paid_predictions()
    assert len(ledger) == 1 and ledger[0]["status"] == "submitted" and ledger[0]["prediction_id"] == "controlled-1"
    register_gate(None)
print("provider gate integration PASS")

# --- Part A5: compatible HTTP headers on Replicate API requests ---------------------------------
captured: list[urllib.request.Request] = []


class FakeResponse(io.BytesIO):
    def __init__(self):
        super().__init__(b"{}")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def capture_urlopen(req, timeout=None):
    captured.append(req)
    return FakeResponse()


with patch.object(urllib.request, "urlopen", capture_urlopen):
    ReplicateGPUProvider._request("GET", "/account", "test-only", None)
assert len(captured) == 1
sent = captured[0]
assert sent.get_header("User-agent") == USER_AGENT, sent.header_items()
assert "DragonFly" in USER_AGENT and "Python-urllib" not in (sent.get_header("User-agent") or "")
assert sent.get_header("Accept") == "application/json", sent.header_items()
assert sent.get_header("Authorization") == "Bearer test-only"
print("replicate request headers PASS")

# --- Part B: end-to-end API safeguards with mocked inference ------------------------------------
DATA_DIR = tempfile.mkdtemp(prefix="dragonfly-paid-gate-api-")
os.environ.update(
    EYE_APP_ENV="test",
    EYE_RECONSTRUCTION_PROVIDER="replicate",
    **GATE_ON,
    REPLICATE_API_TOKEN="test-only",
    EYE_REPLICATE_MODEL_VERSION="owner/model:test-version",
    EYE_RECONSTRUCTION_DEBUG="0",
    EYE_DATA_DIR=DATA_DIR,
    EYE_STORAGE_DURABLE="1",
    EYE_SIGNING_SECRET="test-signing-secret",
    EYE_DAILY_RECONSTRUCTION_QUOTA_PER_USER="5",
    EYE_DAILY_RECONSTRUCTION_QUOTA_PER_GUEST="5",
)

from fastapi.testclient import TestClient  # noqa: E402

import app.runtime as runtime  # noqa: E402

runtime.migrate_legacy_storage = lambda settings: {"copied_files": 0, "conflicts": 0, "database_copied": False}
import app.main as main  # noqa: E402

client = TestClient(main.app)

health = client.get("/health").json()
assert health["inference"]["paid_test"] == {"enabled": True, "environment_allowed": True, "global_limit": 1, "consumed": 0, "remaining": 1, "authorized_user_configured": True}

image_bytes = io.BytesIO()
# Preprocessing requires a reasonably sized, sharp photo; random noise satisfies both.
import random  # noqa: E402

random.seed(7)
noise = Image.new("RGB", (256, 256))
noise.putdata([(random.randrange(256), random.randrange(256), random.randrange(256)) for _ in range(256 * 256)])
noise.save(image_bytes, format="JPEG")


def post_image(headers=None, extra_headers=None):
    files = {"image": ("bottle.jpg", image_bytes.getvalue(), "image/jpeg")}
    all_headers = dict(headers or {})
    all_headers.update(extra_headers or {})
    return client.post("/v1/geometry/generate-from-image", data={"label": "bottle"}, files=files, headers=all_headers)


# Guests are rejected before any job or upload is retained.
response = post_image()
assert response.status_code == 403, response.text
assert response.json()["error_code"] == "paid_test_guest_forbidden"
assert "Guest paid reconstruction is disabled" in response.json()["error"]

# Unauthorized signed-in users are rejected.
intruder_token = client.post("/v1/auth/signup", json={"email": "intruder@example.com", "password": "intruder-pass-123"}).json()["token"]
response = post_image({"Authorization": f"Bearer {intruder_token}"})
assert response.status_code == 403, response.text
assert response.json()["error_code"] == "paid_test_unauthorized_user"
assert "not authorized" in response.json()["error"]

# The authorized existing account may run the single controlled prediction (mocked transport).
pilot_token = client.post("/v1/auth/signup", json={"email": AUTHORIZED, "password": "pilot-pass-12345"}).json()["token"]
pilot_headers = {"Authorization": f"Bearer {pilot_token}"}

transport_posts: list[str] = []


def endpoint_transport(method, path, token, body, absolute=False):
    if method == "POST" and path == "/predictions":
        transport_posts.append(path)
        return {"id": "controlled-api-1", "status": "processing", "urls": {"get": "https://api.replicate.com/v1/predictions/controlled-api-1"}}
    if method == "GET":
        return {"id": "controlled-api-1", "status": "failed", "error": "mock remote failure"}
    raise AssertionError(f"unexpected transport call: {method} {path}")


with patch.object(ReplicateGPUProvider, "_request", staticmethod(endpoint_transport)):
    response = post_image(pilot_headers, {"Idempotency-Key": "controlled-run-1"})
    assert response.status_code == 202, response.text
    job_id = response.json()["job_id"]
    # Replaying the same Idempotency-Key never submits a second prediction.
    replay = post_image(pilot_headers, {"Idempotency-Key": "controlled-run-1"})
    assert replay.status_code == 202 and replay.json()["replayed"] is True and replay.json()["job_id"] == job_id

assert transport_posts == ["/predictions"], transport_posts
job = client.get(f"/v1/geometry/jobs/{job_id}", headers=pilot_headers).json()
assert job["status"] == "error", json.dumps(job)

health = client.get("/health").json()["inference"]["paid_test"]
assert health["consumed"] == 1 and health["remaining"] == 0, health

# The allowance is consumed and persisted: even the authorized account is now rejected.
response = post_image(pilot_headers, {"Idempotency-Key": "controlled-run-2"})
assert response.status_code == 429, response.text
assert response.json()["error_code"] == "paid_test_allowance_exhausted"
assert "allowance is exhausted" in response.json()["error"]

# Restart persistence: a fresh repository on the same database still reports the consumed allowance.
restarted = SqliteRepository(main.RUNTIME.settings.database_path)
assert restarted.count_paid_predictions() == 1

# Existing functionality is preserved: procedural generation, auth, and project listing still work.
response = client.post("/v1/geometry/generate", json={"label": "cup"})
assert response.status_code == 202 and response.json()["provider_kind"] == "procedural_fallback"
assert client.get("/v1/auth/me", headers=pilot_headers).json()["user"]["email"] == AUTHORIZED
assert client.get("/v1/projects", headers=pilot_headers).json()["ok"] is True

print("api safeguards PASS")
print("paid test gate PASS")
