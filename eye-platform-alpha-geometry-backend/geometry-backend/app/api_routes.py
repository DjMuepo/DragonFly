from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from .accounts import AuthError, public_user
from .projects import ProjectError
from .runtime import Runtime


class SignupRequest(BaseModel):
    email: str = Field(max_length=320)
    password: str = Field(max_length=400)
    name: str = Field(default="", max_length=200)


class LoginRequest(BaseModel):
    email: str = Field(max_length=320)
    password: str = Field(max_length=400)


class ProjectClaimRequest(BaseModel):
    from_job_ids: list[str] = Field(min_length=1, max_length=50)
    name: Optional[str] = Field(default=None, max_length=120)


class ProjectPatch(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class CursorRequest(BaseModel):
    index: int = Field(ge=0)


def public_base(request: Request) -> str:
    return (os.environ.get("PUBLIC_BASE_URL") or str(request.base_url)).rstrip("/")


def build_router(runtime: Runtime) -> tuple[APIRouter, dict]:
    router = APIRouter()

    def bearer(request: Request) -> Optional[str]:
        header = request.headers.get("authorization", "")
        return header[7:].strip() if header.lower().startswith("bearer ") else None

    def optional_auth(request: Request):
        token = bearer(request)
        if token is None:
            return None
        authenticated = runtime.auth.authenticate(token)
        if authenticated is None:
            raise HTTPException(status_code=401, detail="Your session has expired. Sign in again.")
        return authenticated

    def required_auth(request: Request):
        authenticated = optional_auth(request)
        if authenticated is None:
            raise HTTPException(status_code=401, detail="Sign in to continue.")
        return authenticated

    def client_ip(request: Request) -> str:
        if runtime.settings.trust_proxy_headers:
            forwarded = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
            if forwarded:
                return forwarded[:64]
        return ""

    def fail(error: Exception):
        status = getattr(error, "status_code", 400)
        return JSONResponse(status_code=status, content={"ok": False, "error": str(error), "detail": str(error)})

    @router.post("/v1/auth/signup")
    def signup(payload: SignupRequest):
        try:
            return {"ok": True, **runtime.auth.signup(payload.email, payload.password, payload.name)}
        except AuthError as error:
            return fail(error)

    @router.post("/v1/auth/login")
    def login(payload: LoginRequest, request: Request):
        try:
            return {"ok": True, **runtime.auth.login(payload.email, payload.password, client_ip(request))}
        except AuthError as error:
            return fail(error)

    @router.post("/v1/auth/logout")
    def logout(auth=Depends(required_auth)):
        runtime.auth.logout(auth[1])
        return {"ok": True}

    @router.get("/v1/auth/me")
    def me(auth=Depends(required_auth)):
        return {"ok": True, "user": public_user(auth[0]), "session_expires_at": auth[1]["expires_at"]}

    @router.get("/v1/projects")
    def list_projects(request: Request, auth=Depends(required_auth)):
        base = public_base(request)
        projects = [runtime.projects.project_view(base, p, include_revisions=False) | {"revision_count": p["revision_count"]} for p in runtime.repo.list_projects(auth[0]["id"])]
        return {"ok": True, "projects": projects}

    @router.post("/v1/projects", status_code=201)
    def save_guest_generation(payload: ProjectClaimRequest, request: Request, auth=Depends(required_auth)):
        try:
            project = runtime.projects.claim_guest_jobs(auth[0], payload.from_job_ids, payload.name, runtime.jobs)
        except ProjectError as error:
            return fail(error)
        return {"ok": True, "project": runtime.projects.project_view(public_base(request), project)}

    @router.get("/v1/projects/{project_id}")
    def get_project(project_id: str, request: Request, auth=Depends(required_auth)):
        try:
            project = runtime.projects.owned_project(auth[0]["id"], project_id)
        except ProjectError as error:
            return fail(error)
        return {"ok": True, "project": runtime.projects.project_view(public_base(request), project)}

    @router.patch("/v1/projects/{project_id}")
    def rename_project(project_id: str, payload: ProjectPatch, request: Request, auth=Depends(required_auth)):
        try:
            runtime.projects.owned_project(auth[0]["id"], project_id)
        except ProjectError as error:
            return fail(error)
        name = payload.name.strip()
        if not name:
            return fail(ProjectError("Project name cannot be empty."))
        import time
        runtime.repo.rename_project(project_id, name, time.time())
        return {"ok": True, "project": runtime.projects.project_view(public_base(request), runtime.repo.get_project(project_id), include_revisions=False)}

    @router.delete("/v1/projects/{project_id}")
    def delete_project(project_id: str, auth=Depends(required_auth)):
        try:
            runtime.projects.delete_project(auth[0]["id"], project_id)
        except ProjectError as error:
            return fail(error)
        return {"ok": True}

    @router.put("/v1/projects/{project_id}/cursor")
    def set_cursor(project_id: str, payload: CursorRequest, request: Request, auth=Depends(required_auth)):
        try:
            project = runtime.projects.set_cursor(auth[0]["id"], project_id, payload.index)
        except ProjectError as error:
            return fail(error)
        return {"ok": True, "project": runtime.projects.project_view(public_base(request), project, include_revisions=False)}

    @router.get("/v1/projects/{project_id}/revisions")
    def revisions(project_id: str, request: Request, auth=Depends(required_auth)):
        try:
            project = runtime.projects.owned_project(auth[0]["id"], project_id)
        except ProjectError as error:
            return fail(error)
        view = runtime.projects.project_view(public_base(request), project)
        return {"ok": True, "cursor_index": view["cursor_index"], "revisions": view["revisions"]}

    @router.get("/v1/projects/{project_id}/source")
    def source_image(project_id: str, auth=Depends(required_auth)):
        try:
            project = runtime.projects.owned_project(auth[0]["id"], project_id)
        except ProjectError as error:
            return fail(error)
        artifact = runtime.repo.get_artifact(project["source_artifact_id"]) if project["source_artifact_id"] else None
        ok, reason = runtime.artifacts.available(artifact)
        if not artifact or not ok:
            raise HTTPException(status_code=404, detail=f"Original photo unavailable: {reason}")
        return FileResponse(runtime.artifacts.path_for(artifact))

    @router.get("/v1/projects/{project_id}/models/{filename}")
    def project_model(project_id: str, filename: str, auth=Depends(required_auth)):
        try:
            runtime.projects.owned_project(auth[0]["id"], project_id)
        except ProjectError as error:
            return fail(error)
        safe_name = Path(filename).name
        artifact = runtime.repo.get_artifact_by_filename(safe_name)
        if not artifact or artifact["project_id"] != project_id or artifact["owner_id"] != auth[0]["id"] or artifact["kind"] not in {"model_glb", "model_stl"}:
            raise HTTPException(status_code=404, detail="Model not found.")
        available, _ = runtime.artifacts.available(artifact)
        if not available:
            raise HTTPException(status_code=404, detail="Model file is unavailable.")
        return FileResponse(runtime.artifacts.path_for(artifact), media_type="model/gltf-binary" if safe_name.lower().endswith(".glb") else "model/stl", filename=safe_name)

    @router.post("/v1/projects/{project_id}/verify")
    def verify_project(project_id: str, auth=Depends(required_auth)):
        try:
            runtime.projects.owned_project(auth[0]["id"], project_id)
        except ProjectError as error:
            return fail(error)
        report = []
        for artifact in runtime.repo.list_project_artifacts(project_id):
            ok, reason = runtime.artifacts.available(artifact, deep=True)
            report.append({"id": artifact["id"], "kind": artifact["kind"], "filename": artifact["filename"], "ok": ok, "reason": reason})
        return {"ok": all(item["ok"] for item in report), "artifacts": report}

    return router, {"optional_auth": optional_auth, "required_auth": required_auth, "public_base": public_base}
