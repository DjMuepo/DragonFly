#!/usr/bin/env python3
from __future__ import annotations

import argparse
import io
import json
import os
import secrets
import stat
import sys
import time
from pathlib import Path

import httpx
from PIL import Image, ImageDraw

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def expect(response: httpx.Response, status: int, action: str) -> httpx.Response:
    require(response.status_code == status, f"{action}: expected HTTP {status}, received {response.status_code}: {response.text[:400]}")
    return response


def image_payload() -> bytes:
    image = Image.new("RGB", (640, 480), "#ddd")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((180, 70, 450, 420), radius=60, fill="#2878b5")
    draw.rectangle((240, 30, 390, 90), fill="#245a88")
    output = io.BytesIO()
    image.save(output, "JPEG", quality=88)
    return output.getvalue()


def wait_job(client: httpx.Client, base: str, job_id: str, token: str, timeout: int) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = client.get(f"{base}/v1/geometry/jobs/{job_id}", headers={"Authorization": f"Bearer {token}"})
        expect(response, 200, "job status")
        job = response.json()
        if job["status"] == "done":
            return job
        if job["status"] == "error":
            raise RuntimeError(f"Job failed safely ({job.get('error_code')}): {job.get('error')}")
        time.sleep(1)
    raise RuntimeError(f"Job {job_id} did not finish within {timeout} seconds")


def smoke_gate(client: httpx.Client, base: str, origin: str, require_backup: bool) -> dict:
    health = expect(client.get(f"{base}/health"), 200, "backend health").json()
    require(health.get("ok") and health.get("storage", {}).get("ready"), "backend storage is not ready")
    require(health.get("storage", {}).get("durable") is True, "EYE_STORAGE_DURABLE=1 and a verified persistent disk are required")
    if require_backup:
        require(health["storage"].get("external_backup_configured") is True, "external backup destination is not configured")
        require(health["storage"].get("restore_tested_attested") is True, "external backup restore drill is not attested")
    inference = health.get("inference", {})
    require(inference.get("environment") == "staging", "backend must identify itself as staging")
    require(inference.get("provider") == "mock-test" and inference.get("mock_enabled") is True, "staging mock provider is not enabled; refusing to submit reconstruction")
    allowed = client.options(f"{base}/v1/auth/me", headers={"Origin": origin, "Access-Control-Request-Method": "GET", "Access-Control-Request-Headers": "authorization"})
    expect(allowed, 200, "allowed CORS preflight")
    denied = client.get(f"{base}/health", headers={"Origin": "https://not-allowed.invalid"})
    expect(denied, 403, "rejected CORS origin")
    return health


def write_state(path: Path, state: dict) -> None:
    path = path.expanduser().resolve()
    require(not path.is_relative_to(REPOSITORY_ROOT), "state file must be outside the repository because it contains a bearer session")
    require(not path.exists(), f"state file already exists; refusing to overwrite: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, stat.S_IRUSR | stat.S_IWUSR)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(state, stream)


def fresh(client: httpx.Client, base: str, state_path: Path) -> None:
    email = f"staging-{secrets.token_hex(6)}@example.invalid"
    password = secrets.token_urlsafe(20)
    signup = expect(client.post(f"{base}/v1/auth/signup", json={"email": email, "password": password, "name": "Staging Smoke"}), 200, "signup").json()
    require(signup.get("ok") and signup.get("token"), "signup did not return a session")
    login = expect(client.post(f"{base}/v1/auth/login", json={"email": email, "password": password}), 200, "login").json()
    token = login["token"]
    headers = {"Authorization": f"Bearer {token}"}
    me = expect(client.get(f"{base}/v1/auth/me", headers=headers), 200, "session restoration").json()
    require(me.get("user", {}).get("email") == email, "session restoration returned a different account")

    generated_response = client.post(
        f"{base}/v1/geometry/generate-from-image",
        headers={**headers, "Idempotency-Key": secrets.token_urlsafe(24)},
        data={"label": "staging bottle", "confidence": "0.5", "quality_mode": "FAST"},
        files={"image": ("staging.jpg", image_payload(), "image/jpeg")},
    )
    expect(generated_response, 202, "mock reconstruction submission")
    generated = wait_job(client, base, generated_response.json()["job_id"], token, 180)
    result = generated.get("result") or {}
    require(result.get("provider_kind") == "mock_test" and str(result.get("notes", "")).startswith("TEST DATA:"), "mock result is not labeled as test data")
    project_id = result.get("project_id")
    require(project_id, "completed mock job did not create a project")

    headers_b = {"Authorization": "Bearer " + expect(client.post(f"{base}/v1/auth/signup", json={"email": f"staging-other-{secrets.token_hex(6)}@example.invalid", "password": secrets.token_urlsafe(20)}), 200, "second-user signup").json()["token"]}
    expect(client.get(f"{base}/v1/projects/{project_id}", headers=headers_b), 404, "cross-user project denial")
    project = expect(client.get(f"{base}/v1/projects/{project_id}", headers=headers), 200, "project save/reopen").json()["project"]
    require(project["revision_count"] == 1 and project["has_source_image"], "initial project/revision/source not persisted")
    revision = project["revisions"][0]
    glb = expect(client.get(revision["model_url"], headers=headers), 200, "authenticated GLB export")
    require(glb.content[:4] == b"glTF", "GLB header is invalid")
    stl_url = result.get("stl_download_url") or revision.get("stl_url")
    expect(client.get(stl_url, headers=headers), 200, "authenticated STL export")

    edit = expect(client.post(f"{base}/v1/geometry/edit", headers={**headers, "Idempotency-Key": secrets.token_urlsafe(24)}, json={"label": "staging bottle", "model_url": revision["model_url"], "project_id": project_id, "prompt": "make it 10% larger"}), 202, "model edit")
    edited = wait_job(client, base, edit.json()["job_id"], token, 60)
    require(edited["result"].get("revision_seq") == 1, "edit revision was not appended")
    calibrated_response = expect(client.post(f"{base}/v1/geometry/calibrate", headers={**headers, "Idempotency-Key": secrets.token_urlsafe(24)}, json={"label": "staging bottle", "model_url": edited["result"]["model_url"], "project_id": project_id, "measurement": "This bottle is 100 mm tall."}), 202, "physical calibration")
    calibrated = wait_job(client, base, calibrated_response.json()["job_id"], token, 60)
    require(calibrated["result"].get("scale_status") == "calibrated", "calibration metadata missing")
    state = {"email": email, "password": password, "project_id": project_id, "token": token, "revision_count": 3}
    write_state(state_path, state)
    print(json.dumps({"phase": "fresh", "project_id": project_id, "revision_count": 3, "provider_kind": result["provider_kind"], "state_file": str(state_path)}))


def after_restart(client: httpx.Client, base: str, state_path: Path) -> None:
    state_path = state_path.expanduser().resolve()
    require(not state_path.is_relative_to(REPOSITORY_ROOT), "state file must be outside the repository")
    require(state_path.is_file(), f"state file not found: {state_path}")
    if os.name == "posix":
        require(stat.S_IMODE(state_path.stat().st_mode) == 0o600, "state file permissions must be 0600")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    token = state["token"]
    headers = {"Authorization": f"Bearer {token}"}
    expect(client.get(f"{base}/v1/auth/me", headers=headers), 200, "session persistence after restart")
    project = expect(client.get(f"{base}/v1/projects/{state['project_id']}", headers=headers), 200, "project persistence after restart").json()["project"]
    require(project["revision_count"] == state["revision_count"] and len(project["revisions"]) == state["revision_count"], "revision history did not survive restart")
    require(project["revisions"][-1]["scale_status"] == "calibrated", "calibration metadata did not survive restart")
    export = expect(client.get(project["revisions"][-1]["model_url"], headers=headers), 200, "post-restart GLB export")
    require(export.content[:4] == b"glTF", "post-restart GLB is invalid")
    expect(client.post(f"{base}/v1/auth/logout", headers=headers), 200, "logout")
    expect(client.get(f"{base}/v1/auth/me", headers=headers), 401, "logout revocation")
    state_path.unlink()
    print(json.dumps({"phase": "after-restart", "project_id": state["project_id"], "revision_count": state["revision_count"], "session_revoked": True}))


def main() -> None:
    parser = argparse.ArgumentParser(description="No-paid-inference DragonFly staging smoke test")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--frontend-origin", required=True)
    parser.add_argument("--phase", choices=("fresh", "after-restart"), required=True)
    parser.add_argument("--state-file", required=True, type=Path, help="Use a private path outside the repository; fresh phase stores a bearer session until the restart phase")
    parser.add_argument("--require-backup", action="store_true", help="Require external backup and restore-test attestation from /health")
    args = parser.parse_args()
    with httpx.Client(timeout=httpx.Timeout(30, connect=10), follow_redirects=False) as client:
        smoke_gate(client, args.base_url.rstrip("/"), args.frontend_origin, args.require_backup)
        if args.phase == "fresh":
            fresh(client, args.base_url.rstrip("/"), args.state_file)
        else:
            after_restart(client, args.base_url.rstrip("/"), args.state_file)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"staging smoke failed: {error}", file=sys.stderr)
        raise SystemExit(1)
