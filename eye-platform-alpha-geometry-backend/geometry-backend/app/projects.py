from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Optional

from .artifacts import ArtifactStore
from .durable_jobs import JobRecord
from .persistence.repository import DuplicateError, Repository, Row
from .physical_units import ScaleMetadata, metadata_path, save_scale_metadata

URL_KEYS = ("model_url", "download_url", "stl_download_url")


class ProjectError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def _loads(value: Optional[str]) -> Any:
    return json.loads(value) if value else None


def _error_patch(message: str, code: str) -> dict:
    return {"status": "error", "progress": 100, "stage": "error", "stage_detail": message, "error": message, "error_code": code, "result": None}


class ProjectService:
    def __init__(self, repo: Repository, artifacts: ArtifactStore):
        self.repo = repo
        self.artifacts = artifacts

    @property
    def models_dir(self) -> Path:
        return self.artifacts.settings.models_dir

    # ownership
    def owned_project(self, user_id: str, project_id: str) -> Row:
        project = self.repo.get_project(project_id)
        if not project or project["owner_id"] != user_id:
            raise ProjectError("Project not found.", 404)
        return project

    def authorize_model(self, user: Optional[Row], model_filename: str, project_id: Optional[str]) -> tuple[Optional[Row], Optional[Row]]:
        """Return (project, revision) when the model belongs to a saved project, enforcing ownership."""
        artifact = self.repo.get_artifact_by_filename(model_filename)
        if artifact is None:
            if project_id:
                raise ProjectError("That model is not part of the project.", 400)
            return None, None
        if user is None or artifact["owner_id"] != user["id"] or (project_id and artifact["project_id"] != project_id):
            raise ProjectError("Model not found.", 404)
        project = self.repo.get_project(artifact["project_id"])
        revision = next((r for r in self.repo.list_revisions(artifact["project_id"], include_superseded=True) if r["model_artifact_id"] == artifact["id"]), None)
        if project is None or revision is None:
            raise ProjectError("Model not found.", 404)
        if revision["superseded_at"] is not None:
            raise ProjectError("That revision was replaced by a newer edit. Reopen the project and try again.", 409)
        return project, revision

    def restore_sidecars(self, revision: Row) -> None:
        """Rebuild scale/feature sidecar files from database truth if the disk copy is missing."""
        model = self.repo.get_artifact(revision["model_artifact_id"])
        if not model:
            return
        path = self.artifacts.path_for(model)
        if not path.is_file():
            return
        if not metadata_path(path).is_file():
            calibration = _loads(revision["calibration_json"])
            if revision["scale_status"] == "calibrated" and calibration:
                save_scale_metadata(path, ScaleMetadata(status="calibrated", calibrated_axis=calibration.get("axis"), calibrated_value_mm=calibration.get("value_mm"), source_measurement=calibration.get("source_measurement")))
            else:
                save_scale_metadata(path, ScaleMetadata())
        features = (_loads(revision["metadata_json"]) or {}).get("features")
        feature_path = path.with_suffix(".features.json")
        if features and not feature_path.is_file():
            feature_path.write_text(json.dumps(features, separators=(",", ":")), encoding="utf-8")

    # job completion hook
    def finalize_job(self, job: JobRecord, changes: dict) -> dict:
        result = changes.get("result") or {}
        model_name = Path(result.get("model_name", "")).name
        model_path = self.models_dir / model_name
        if not model_name or not model_path.is_file() or model_path.stat().st_size == 0:
            return _error_patch("The generated model file is missing from storage. Nothing was saved; try again.", "artifact_missing")
        if job.owner_id is None:
            return {}
        project = self.repo.get_project(job.project_id) if job.project_id else None
        if job.kind != "generate" and project is None:
            return _error_patch("The project for this edit no longer exists.", "project_missing")
        return self._commit(job, result, project, job.extra.get("base_seq"))

    def _commit(self, job: JobRecord, result: dict, project: Optional[Row], base_seq: Optional[int]) -> dict:
        owner_id = job.owner_id or ""
        created_project = False
        model_path = self.models_dir / Path(result["model_name"]).name
        if project is None:
            project = self.repo.create_project(uuid.uuid4().hex, owner_id, (job.extra.get("project_name") or result.get("label") or "Untitled project")[:120], (result.get("label") or "Object")[:80], time.time())
            created_project = True
        try:
            glb = self.artifacts.register(owner_id, project["id"], "model_glb", model_path)
            stl_path = model_path.with_suffix(".stl")
            stl = self.artifacts.register(owner_id, project["id"], "model_stl", stl_path) if stl_path.is_file() else None
            for sidecar in (model_path.with_suffix(".metadata.json"), model_path.with_suffix(".features.json")):
                if sidecar.is_file():
                    self.artifacts.register(owner_id, project["id"], "sidecar", sidecar)
            source_file = job.extra.get("source_file")
            if created_project and source_file:
                source_path = self.artifacts.settings.sources_dir / Path(source_file).name
                if source_path.is_file():
                    source = self.artifacts.register(owner_id, project["id"], "source_image", source_path)
                    self.repo.set_project_source(project["id"], source["id"])
            feature_path = model_path.with_suffix(".features.json")
            try:
                features = json.loads(feature_path.read_text(encoding="utf-8")) if feature_path.is_file() else {}
            except (OSError, json.JSONDecodeError):
                features = {}
            stored = {key: value for key, value in result.items() if key not in URL_KEYS}
            revision = self.repo.append_revision(
                project["id"],
                {
                    "id": uuid.uuid4().hex, "kind": {"generate": "generate", "edit": "edit", "calibrate": "calibration"}.get(job.kind, job.kind), "job_id": job["job_id"],
                    "model_artifact_id": glb["id"], "stl_artifact_id": stl["id"] if stl else None, "provider": result.get("engine"), "provider_kind": result.get("provider_kind"),
                    "change_kind": result.get("change_kind"), "summary": result.get("edit_summary") or result.get("notes"), "scale_status": result.get("scale_status") or "unknown",
                    "calibration_json": json.dumps(result["calibration"]) if result.get("calibration") else None,
                    "validation_json": json.dumps(result["validation"]) if result.get("validation") else None,
                    "metadata_json": json.dumps({"result": stored, "features": features}),
                },
                base_seq, time.time(),
            )
        except Exception:
            if created_project:
                self.artifacts.delete_files(self.repo.delete_project(project["id"]))
            raise
        return {"project_id": project["id"], "result": {**result, "project_id": project["id"], "revision_id": revision["id"], "revision_seq": revision["seq"]}}

    def claim_guest_jobs(self, user: Row, job_ids: list[str], name: Optional[str], jobs) -> Row:
        records = [jobs.get(job_id) for job_id in job_ids]
        if not records or any(r is None or r.owner_id is not None or r["status"] != "done" or not r["result"] for r in records):
            raise ProjectError("Only finished guest jobs can be saved. Regenerate the model after signing in.", 409)
        if records[0].kind != "generate":
            raise ProjectError("The first saved job must be the original generation.", 400)
        project: Optional[Row] = None
        for record in records:
            if not self.repo.claim_job(record["job_id"], user["id"], time.time()):
                raise ProjectError("That job was already saved.", 409)
            record.owner_id = user["id"]
            record.extra = {**record.extra, "project_name": name}
            patch = self.finalize_job(record, {"result": record["result"], "status": "done"}) if project is None else {}
            if project is not None:
                tip = max((r["seq"] for r in self.repo.list_revisions(project["id"])), default=None)
                patch = self._commit(record, record["result"], project, tip)
            if patch.get("status") == "error":
                raise ProjectError(patch["error"], 409)
            record.update(**{k: v for k, v in patch.items() if k in ("result", "project_id")})
            project = self.repo.get_project(patch["project_id"])
        assert project is not None
        return project

    # presentation
    def signed_url(self, base_url: str, filename: str) -> str:
        return f"{base_url}/v1/geometry/models/{filename}?{self.artifacts.signed_query(filename)}"

    def sign_result(self, base_url: str, result: Optional[dict]) -> Optional[dict]:
        if not result or not result.get("project_id"):
            return result
        signed = dict(result)
        name = Path(result.get("model_name", "")).name
        signed["model_url"] = signed["download_url"] = self.signed_url(base_url, name)
        if result.get("stl_download_url"):
            signed["stl_download_url"] = self.signed_url(base_url, Path(result["stl_download_url"].split("?")[0]).name)
        return signed

    def revision_view(self, base_url: str, revision: Row) -> dict:
        model = self.repo.get_artifact(revision["model_artifact_id"])
        stl = self.repo.get_artifact(revision["stl_artifact_id"]) if revision["stl_artifact_id"] else None
        available, reason = self.artifacts.available(model)
        stored = (_loads(revision["metadata_json"]) or {}).get("result", {})
        view = {
            "id": revision["id"], "seq": revision["seq"], "kind": revision["kind"], "job_id": revision["job_id"], "provider": revision["provider"],
            "provider_kind": revision["provider_kind"], "change_kind": revision["change_kind"], "summary": revision["summary"], "scale_status": revision["scale_status"],
            "calibration": _loads(revision["calibration_json"]), "validation": _loads(revision["validation_json"]), "created_at": revision["created_at"],
            "model_name": model["filename"] if model else None, "available": available, "unavailable_reason": None if available else reason,
            "operations": stored.get("operations", []), "warnings": list(((stored.get("reconstruction_quality") or {}).get("warnings")) or []),
            "hidden_surface_uncertainty": stored.get("hidden_surface_uncertainty"), "label": stored.get("label"),
        }
        if available and model:
            view["model_url"] = self.signed_url(base_url, model["filename"])
            if stl and self.artifacts.available(stl)[0]:
                view["stl_url"] = self.signed_url(base_url, stl["filename"])
        return view

    def project_view(self, base_url: str, project: Row, include_revisions: bool = True) -> dict:
        revisions = self.repo.list_revisions(project["id"])
        data = {
            "id": project["id"], "name": project["name"], "label": project["label"], "created_at": project["created_at"], "updated_at": project["updated_at"],
            "cursor_index": min(project["cursor_index"], max(len(revisions) - 1, 0)), "revision_count": len(revisions), "has_source_image": bool(project["source_artifact_id"]),
        }
        if include_revisions:
            data["revisions"] = [self.revision_view(base_url, r) for r in revisions]
        return data

    def delete_project(self, user_id: str, project_id: str) -> None:
        self.owned_project(user_id, project_id)
        self.artifacts.delete_files(self.repo.delete_project(project_id))

    def set_cursor(self, user_id: str, project_id: str, index: int) -> Row:
        project = self.owned_project(user_id, project_id)
        count = len(self.repo.list_revisions(project_id))
        if not 0 <= index < count:
            raise ProjectError("Revision position is out of range.", 400)
        self.repo.set_cursor(project_id, index, time.time())
        return self.repo.get_project(project["id"])  # type: ignore[return-value]
