"""Core integration tests: auth, projects, durable jobs, artifacts. Inference is mocked; no paid requests are made.

Run: PYTHONPATH=. python tests/core_integration_test.py
"""
import hashlib
from concurrent.futures import ThreadPoolExecutor
import io
import os
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import trimesh
from PIL import Image

PHASE = sys.argv[1] if len(sys.argv) > 1 else "all"
DATA_DIR = sys.argv[2] if len(sys.argv) > 2 else None
if PHASE == "all":
    DATA_DIR = tempfile.mkdtemp(prefix="dragonfly-core-")
os.environ.update(EYE_DATA_DIR=DATA_DIR, EYE_STORAGE_DURABLE="1", EYE_SIGNING_SECRET="test-signing-secret", EYE_REQUIRE_DURABLE_STORAGE="1", EYE_UPLOAD_MAX_BYTES=str(2 * 1024 * 1024), EYE_DAILY_RECONSTRUCTION_QUOTA_PER_USER="5", EYE_DAILY_RECONSTRUCTION_QUOTA_PER_GUEST="2")

from fastapi.testclient import TestClient  # noqa: E402

import app.runtime as runtime  # noqa: E402
runtime.migrate_legacy_storage = lambda settings: {"copied_files": 0, "conflicts": 0, "database_copied": False}
import app.main as main  # noqa: E402
from app.providers import ReconstructionOutput  # noqa: E402
from app.persistence.repository import QuotaExceeded  # noqa: E402

PROVIDER_CALLS = []
FAIL_NEXT = {"on": False}


class FakeProvider:
    name = "replicate-remote-gpu"


def fake_reconstruct(request, models_dir, allow_procedural_fallback=False):
    PROVIDER_CALLS.append(request.job_id)
    if FAIL_NEXT["on"]:
        raise RuntimeError("mock provider failure")
    from app.mesh_factory import export_trimesh
    mesh = trimesh.creation.cylinder(radius=0.03, height=0.1, sections=48)
    name, path = export_trimesh(mesh, request.label, models_dir)
    return ReconstructionOutput(engine="replicate-remote-gpu", model_name=name, model_path=path, stl_name=path.with_suffix(".stl").name, stl_path=path.with_suffix(".stl"), detected_family="bottle", notes="mock", provider_kind="ai", validation=None, reconstruction_quality={"status": "warning", "fidelity_verified": False, "warnings": ["mock warning"], "limitation": "mock"})


main.reconstruct = fake_reconstruct
main.select_provider = lambda: FakeProvider()
client = TestClient(main.app)
RUNTIME = main.RUNTIME
DB = RUNTIME.settings.database_path


def photo_bytes(color=(180, 90, 40)) -> bytes:
    import numpy as np
    rng = np.random.default_rng(sum(color))
    pixels = rng.integers(0, 255, (480, 640, 3), dtype=np.uint8)
    pixels[120:360, 200:440] = color
    buffer = io.BytesIO()
    Image.fromarray(pixels).save(buffer, format="JPEG")
    return buffer.getvalue()


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def signup(email, password="correct horse battery", name="Tester"):
    response = client.post("/v1/auth/signup", json={"email": email, "password": password, "name": name})
    assert response.status_code == 200, response.text
    return response.json()["token"]


def generate(token=None, key=None, image=None):
    headers = auth(token) if token else {}
    if key:
        headers["Idempotency-Key"] = key
    response = client.post("/v1/geometry/generate-from-image", headers=headers, data={"label": "bottle"}, files={"image": ("scan.jpg", image or photo_bytes(), "image/jpeg")})
    assert response.status_code == 202, response.text
    return response.json()


def job(job_id, token=None):
    return client.get(f"/v1/geometry/jobs/{job_id}", headers=auth(token) if token else {})


def edit(token, project_id, model_url, prompt="make it 20% larger"):
    response = client.post("/v1/geometry/edit", headers=auth(token), json={"label": "bottle", "model_url": model_url, "prompt": prompt, "project_id": project_id})
    assert response.status_code == 202, response.text
    return job(response.json()["job_id"], token).json()


def calibrate(token, project_id, model_url, measurement="This bottle is 180 mm tall."):
    response = client.post("/v1/geometry/calibrate", headers=auth(token), json={"label": "bottle", "model_url": model_url, "measurement": measurement, "project_id": project_id})
    assert response.status_code == 202, response.text
    return job(response.json()["job_id"], token).json()


def project(token, project_id):
    response = client.get(f"/v1/projects/{project_id}", headers=auth(token))
    assert response.status_code == 200, response.text
    return response.json()["project"]


def run_all():
    # --- Signup, login, logout, revocation, expiry, throttling
    assert client.post("/v1/auth/signup", json={"email": "bad", "password": "correct horse battery"}).status_code == 400
    assert client.post("/v1/auth/signup", json={"email": "weak@example.com", "password": "short"}).status_code == 400
    token_a = signup("a@example.com")
    assert client.post("/v1/auth/signup", json={"email": "A@example.com", "password": "correct horse battery"}).status_code == 409
    assert client.get("/v1/auth/me", headers=auth(token_a)).json()["user"]["email"] == "a@example.com"
    stored_hash = RUNTIME.repo.get_user_by_email("a@example.com")["password_hash"]
    assert stored_hash.startswith("scrypt$") and "correct horse" not in stored_hash
    login = client.post("/v1/auth/login", json={"email": "a@example.com", "password": "correct horse battery"})
    assert login.status_code == 200 and login.json()["token"] != token_a
    token_a2 = login.json()["token"]
    assert client.post("/v1/auth/logout", headers=auth(token_a2)).status_code == 200
    assert client.get("/v1/auth/me", headers=auth(token_a2)).status_code == 401, "revoked token must fail"
    assert client.get("/v1/auth/me", headers=auth(token_a)).status_code == 200, "other session must survive logout"
    conn = sqlite3.connect(DB)
    conn.execute("UPDATE sessions SET expires_at = ? WHERE token_hash = ?", (time.time() - 5, hashlib.sha256(token_a.encode()).hexdigest()))
    conn.commit(); conn.close()
    assert client.get("/v1/auth/me", headers=auth(token_a)).status_code == 401, "expired token must fail"
    assert client.get("/v1/projects").status_code == 401
    assert client.get("/v1/projects", headers=auth("forged")).status_code == 401
    token_a = client.post("/v1/auth/login", json={"email": "a@example.com", "password": "correct horse battery"}).json()["token"]
    owner_a = RUNTIME.repo.get_user_by_email("a@example.com")
    def contend(_):
        try:
            return RUNTIME.jobs.create("generate", owner_a["id"], "mock", "ai")
        except QuotaExceeded:
            return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        contenders = list(pool.map(contend, range(2)))
    admitted = [entry for entry in contenders if entry is not None]
    assert len(admitted) == 1, "concurrent active-job limit must be atomic"
    held, _ = admitted[0]
    limited = client.post("/v1/geometry/generate-from-image", headers=auth(token_a), data={"label": "bottle"}, files={"image": ("scan.jpg", photo_bytes(), "image/jpeg")})
    assert limited.status_code == 429 and limited.json()["error_code"] == "active_job_limit"
    RUNTIME.repo.update_job(held["job_id"], {"status": "error", "error": "test cleanup"}, time.time())
    def idempotent_contender(_):
        return RUNTIME.jobs.create("generate", owner_a["id"], "mock", "ai", extra={"fingerprint": "same"}, idempotency_key="concurrent-key")
    with ThreadPoolExecutor(max_workers=4) as pool:
        duplicates = list(pool.map(idempotent_contender, range(4)))
    assert len({entry[0]["job_id"] for entry in duplicates}) == 1
    assert sorted(entry[1] for entry in duplicates).count(True) == 1
    RUNTIME.repo.update_job(duplicates[0][0]["job_id"], {"status": "error", "error": "test cleanup"}, time.time())
    too_large = client.post("/v1/geometry/generate-from-image", headers=auth(token_a), data={"label": "bottle"}, files={"image": ("large.jpg", b"x" * (2 * 1024 * 1024 + 10), "image/jpeg")})
    assert too_large.status_code == 413
    for _ in range(5):
        assert client.post("/v1/auth/login", json={"email": "a@example.com", "password": "wrong password!"}).status_code == 401
    assert client.post("/v1/auth/login", json={"email": "a@example.com", "password": "correct horse battery"}).status_code == 429
    RUNTIME.auth.limiter.clear("a@example.com", "")

    # --- Generate -> save -> reopen
    original_photo = photo_bytes()
    created = generate(token_a, key="gen-1", image=original_photo)
    done = job(created["job_id"], token_a).json()
    assert done["status"] == "done", done
    result = done["result"]
    project_id = result["project_id"]
    assert result["revision_seq"] == 0 and result["provider_kind"] == "ai" and f"/v1/projects/{project_id}/models/" in result["model_url"] and "?" not in result["model_url"]
    assert len(PROVIDER_CALLS) == 1
    reopened = project(token_a, project_id)
    assert reopened["revision_count"] == 1 and reopened["has_source_image"] and reopened["revisions"][0]["kind"] == "generate"
    assert reopened["revisions"][0]["warnings"] == ["mock warning"] and reopened["revisions"][0]["available"]
    assert client.get(f"/v1/projects/{project_id}/source", headers=auth(token_a)).content == original_photo, "original source photo must be preserved"
    assert client.get(reopened["revisions"][0]["model_url"]).status_code == 401
    glb = client.get(reopened["revisions"][0]["model_url"], headers=auth(token_a))
    assert glb.status_code == 200 and trimesh.load(io.BytesIO(glb.content), file_type="glb", force="mesh").is_watertight
    listing = client.get("/v1/projects", headers=auth(token_a)).json()["projects"]
    assert [p["id"] for p in listing] == [project_id] and listing[0]["revision_count"] == 1

    # --- Idempotent retry: no second paid inference
    replay = generate(token_a, key="gen-1", image=original_photo)
    assert replay["job_id"] == created["job_id"] and replay["replayed"] and len(PROVIDER_CALLS) == 1
    recovered = client.get("/v1/geometry/idempotency", headers={**auth(token_a), "Idempotency-Key": "gen-1"})
    assert recovered.status_code == 200 and recovered.json()["job_id"] == created["job_id"] and recovered.json()["replayed"]
    conflict = client.post("/v1/geometry/generate-from-image", headers={**auth(token_a), "Idempotency-Key": "gen-1"}, data={"label": "bottle"}, files={"image": ("scan.jpg", photo_bytes((1, 2, 3)), "image/jpeg")})
    assert conflict.status_code == 409 and len(PROVIDER_CALLS) == 1
    confidence_conflict = client.post("/v1/geometry/generate-from-image", headers={**auth(token_a), "Idempotency-Key": "gen-1"}, data={"label": "bottle", "confidence": "0.8"}, files={"image": ("scan.jpg", original_photo, "image/jpeg")})
    assert confidence_conflict.status_code == 409 and len(PROVIDER_CALLS) == 1

    # --- Ownership: user B cannot see or touch A's data
    token_b = signup("b@example.com")
    assert client.get("/v1/geometry/idempotency", headers={**auth(token_b), "Idempotency-Key": "gen-1"}).status_code == 404
    assert client.get("/v1/projects", headers=auth(token_b)).json()["projects"] == []
    for method, path, body in [("get", f"/v1/projects/{project_id}", None), ("patch", f"/v1/projects/{project_id}", {"name": "stolen"}), ("delete", f"/v1/projects/{project_id}", None), ("put", f"/v1/projects/{project_id}/cursor", {"index": 0}), ("get", f"/v1/projects/{project_id}/revisions", None), ("get", f"/v1/projects/{project_id}/source", None), ("post", f"/v1/projects/{project_id}/verify", None)]:
        response = getattr(client, method)(path, headers=auth(token_b), **({"json": body} if body else {}))
        assert response.status_code == 404, (method, path, response.status_code)
    assert job(created["job_id"], token_b).status_code == 404 and job(created["job_id"]).status_code == 404
    model_name = reopened["revisions"][0]["model_name"]
    assert client.get(f"/v1/geometry/models/{model_name}").status_code == 404, "unsigned access to a project file must fail"
    assert client.get(f"/v1/geometry/models/{model_name}", headers=auth(token_b)).status_code == 404
    assert client.get(f"/v1/geometry/models/{model_name}?exp=9999999999&sig=deadbeef").status_code == 404
    assert client.get(f"/v1/geometry/models/{model_name}?exp=1&sig=anything").status_code == 404
    assert client.get(f"/v1/geometry/models/{model_name}", headers=auth(token_a)).status_code == 200
    stolen = client.post("/v1/geometry/edit", headers=auth(token_b), json={"model_url": reopened["revisions"][0]["model_url"], "prompt": "make it 20% larger"})
    assert stolen.status_code == 404
    assert client.post("/v1/geometry/edit", json={"model_url": reopened["revisions"][0]["model_url"], "prompt": "make it 20% larger"}).status_code == 404

    # --- Edit -> save -> reopen; calibration persistence; export integrity
    first_edit = edit(token_a, project_id, reopened["revisions"][0]["model_url"])
    assert first_edit["status"] == "done" and first_edit["result"]["revision_seq"] == 1, first_edit
    calibrated = calibrate(token_a, project_id, first_edit["result"]["model_url"])
    assert calibrated["status"] == "done" and calibrated["result"]["revision_seq"] == 2, calibrated
    state = project(token_a, project_id)
    assert state["revision_count"] == 3 and state["cursor_index"] == 2
    rev = state["revisions"][2]
    assert rev["scale_status"] == "calibrated" and rev["calibration"]["value_mm"] == 180 and rev["validation"]["dimensions_mm"]["height"] == 180
    assert state["revisions"][0]["scale_status"] == "unknown" and state["revisions"][1]["change_kind"] == "geometry"
    stl_response = client.get(rev["stl_url"], headers=auth(token_a))
    assert stl_response.status_code == 200
    stl = trimesh.load(io.BytesIO(stl_response.content), file_type="stl", force="mesh")
    assert abs(stl.extents[2] - 180) < 0.01, "STL export must stay in millimetres"
    glb_response = client.get(rev["model_url"], headers=auth(token_a))
    assert glb_response.status_code == 200
    glb2 = trimesh.load(io.BytesIO(glb_response.content), file_type="glb", force="mesh")
    assert abs(glb2.extents[2] - 0.18) < 1e-5
    verify = client.post(f"/v1/projects/{project_id}/verify", headers=auth(token_a)).json()
    assert verify["ok"] and any(a["kind"] == "source_image" for a in verify["artifacts"])

    # --- Undo / redo / reset persist; a new edit from an earlier revision supersedes the redo tail
    for index in (1, 2, 0):
        assert client.put(f"/v1/projects/{project_id}/cursor", headers=auth(token_a), json={"index": index}).json()["project"]["cursor_index"] == index
    assert client.put(f"/v1/projects/{project_id}/cursor", headers=auth(token_a), json={"index": 9}).status_code == 400
    branch = edit(token_a, project_id, project(token_a, project_id)["revisions"][0]["model_url"], "make it 50% larger")
    assert branch["status"] == "done"
    state = project(token_a, project_id)
    assert [r["seq"] for r in state["revisions"]] == [0, 3] and state["cursor_index"] == 1
    assert len(RUNTIME.repo.list_revisions(project_id, include_superseded=True)) == 4, "superseded revisions are retained"
    stale = client.post("/v1/geometry/edit", headers=auth(token_a), json={"model_url": rev["model_url"], "prompt": "make it 20% larger", "project_id": project_id})
    assert stale.status_code == 409, "editing a superseded revision must be refused"
    assert len(PROVIDER_CALLS) == 1, "edits must never trigger reconstruction"

    # --- Rename
    renamed = client.patch(f"/v1/projects/{project_id}", headers=auth(token_a), json={"name": "My bottle"})
    assert renamed.json()["project"]["name"] == "My bottle"
    assert client.patch(f"/v1/projects/{project_id}", headers=auth(token_a), json={"name": "  "}).status_code in (400, 422)

    # --- Failed reconstruction: explicit error, no project, no procedural substitution, source photo discarded
    before = len(client.get("/v1/projects", headers=auth(token_a)).json()["projects"])
    sources_before = set(os.listdir(RUNTIME.settings.sources_dir))
    FAIL_NEXT["on"] = True
    failed = job(generate(token_a, key="gen-fail")["job_id"], token_a).json()
    FAIL_NEXT["on"] = False
    assert failed["status"] == "error" and failed["result"] is None and failed["error_code"] == "provider_outcome_unknown" and "mock provider failure" not in failed["error"] and failed["provider_kind"] == "ai"
    assert len(client.get("/v1/projects", headers=auth(token_a)).json()["projects"]) == before
    assert set(os.listdir(RUNTIME.settings.sources_dir)) == sources_before
    retry = job(generate(token_a, key="gen-fail-retry")["job_id"], token_a).json()
    assert retry["status"] == "done", "an explicit retry with a new key runs a fresh job"
    over_quota = client.post("/v1/geometry/generate-from-image", headers=auth(token_a), data={"label": "bottle"}, files={"image": ("scan.jpg", original_photo, "image/jpeg")})
    assert over_quota.status_code == 429 and over_quota.json()["error_code"] == "daily_quota"

    # --- Missing artifact handling
    victim = retry["result"]
    victim_state = project(token_a, victim["project_id"])
    (RUNTIME.settings.models_dir / victim_state["revisions"][0]["model_name"]).unlink()
    assert job(retry["job_id"], token_a).json()["status"] == "error" and job(retry["job_id"], token_a).json()["error_code"] == "artifact_missing"
    reopened_missing = project(token_a, victim["project_id"])["revisions"][0]
    assert reopened_missing["available"] is False and "missing" in reopened_missing["unavailable_reason"] and "model_url" not in reopened_missing
    assert client.get(f"/v1/geometry/models/{victim_state['revisions'][0]['model_name']}", headers=auth(token_a)).status_code == 404
    assert any(not item["ok"] for item in client.post(f"/v1/projects/{victim['project_id']}/verify", headers=auth(token_a)).json()["artifacts"])
    fake = type("J", (), {"owner_id": "x", "project_id": None, "kind": "generate", "extra": {}})()
    assert RUNTIME.projects.finalize_job(fake, {"result": {"model_name": "nope.glb"}})["error_code"] == "artifact_missing"
    FAIL_NEXT["on"] = False

    # --- Guest generation can be saved after sign-in; claims cannot be replayed or stolen
    guest = generate()
    guest_done = job(guest["job_id"]).json()
    assert guest_done["status"] == "done" and "project_id" not in (guest_done["result"] or {}) or guest_done["result"]["project_id"] is None
    guest_edit = client.post("/v1/geometry/edit", json={"model_url": guest_done["result"]["model_url"], "prompt": "make it 20% larger"})
    guest_edit_done = job(guest_edit.json()["job_id"]).json()
    assert guest_edit_done["status"] == "done"
    claimed = client.post("/v1/projects", headers=auth(token_b), json={"from_job_ids": [guest["job_id"], guest_edit.json()["job_id"]], "name": "Saved from guest"})
    assert claimed.status_code == 201, claimed.text
    claimed_project = claimed.json()["project"]
    assert claimed_project["revision_count"] == 2 and not claimed_project["has_source_image"]
    assert client.post("/v1/projects", headers=auth(token_a), json={"from_job_ids": [guest["job_id"]]}).status_code == 409
    assert client.post("/v1/projects", headers=auth(token_a), json={"from_job_ids": [created["job_id"]]}).status_code == 409, "owned jobs cannot be claimed"

    # --- Interrupted job left behind for the restart phase
    now = time.time()
    RUNTIME.repo.create_job({"id": "crashedjob01", "owner_scope": "guest", "kind": "generate", "status": "processing", "progress": 40, "provider": "replicate-remote-gpu", "provider_kind": "ai", "quality_mode": "STANDARD", "extra_json": "{}", "attempts": 1, "created_at": now, "updated_at": now})
    return {"project_id": project_id, "model_name": project(token_a, project_id)["revisions"][1]["model_name"], "token_a": token_a, "token_b": token_b, "claimed": claimed_project["id"]}


def phase_restart_verify(state):
    # New process, same data directory: sessions, projects, history, calibration and jobs must survive.
    assert RUNTIME.repo.migrate() == [], "migrations must be idempotent"
    with TestClient(main.app) as live:  # triggers startup recovery
        pass
    me = client.get("/v1/auth/me", headers=auth(state["token_a"]))
    assert me.status_code == 200, "sessions must survive restart"
    reopened = project(state["token_a"], state["project_id"])
    assert reopened["name"] == "My bottle" and [r["seq"] for r in reopened["revisions"]] == [0, 3] and reopened["cursor_index"] == 1
    assert reopened["revisions"][0]["available"] and reopened["revisions"][1]["available"]
    assert client.get(reopened["revisions"][1]["model_url"], headers=auth(state["token_a"])).status_code == 200
    crashed = client.get("/v1/geometry/jobs/crashedjob01").json()
    assert crashed["status"] == "error" and crashed["error_code"] == "interrupted" and not PROVIDER_CALLS, "interrupted jobs fail closed without re-running inference"
    continued = edit(state["token_a"], state["project_id"], reopened["revisions"][1]["model_url"], "make it 10% larger")
    assert continued["status"] == "done" and continued["result"]["revision_seq"] == 4, "editing continues after restart without reconstruction"
    assert not PROVIDER_CALLS
    calibrated_project = project(state["token_b"], state["claimed"])
    assert calibrated_project["revision_count"] == 2
    cal = calibrate(state["token_a"], state["project_id"], continued["result"]["model_url"])
    assert cal["status"] == "done" and cal["result"]["scale_status"] == "calibrated", cal
    sidecar = RUNTIME.settings.models_dir / Path(cal["result"]["model_name"]).with_suffix(".metadata.json").name
    sidecar.unlink()
    again = edit(state["token_a"], state["project_id"], project(state["token_a"], state["project_id"])["revisions"][-1]["model_url"], "make it 10% larger")
    assert again["status"] == "done" and again["result"]["scale_status"] == "calibrated", "scale metadata is restored from the database"
    # Deleting removes rows and files
    assert client.delete(f"/v1/projects/{state['project_id']}", headers=auth(state["token_a"])).status_code == 200
    assert client.get(f"/v1/projects/{state['project_id']}", headers=auth(state["token_a"])).status_code == 404
    assert not (RUNTIME.settings.models_dir / state["model_name"]).exists()
    print("core integration restart phase PASS")


if PHASE == "all":
    saved = run_all()
    import json
    env = {**os.environ}
    result = subprocess.run([sys.executable, __file__, "restart", DATA_DIR, json.dumps(saved)], env=env, capture_output=True, text=True)
    print(result.stdout[-2000:])
    assert result.returncode == 0, result.stderr[-4000:]
    print("core integration PASS")
else:
    import json
    phase_restart_verify(json.loads(sys.argv[3]))
