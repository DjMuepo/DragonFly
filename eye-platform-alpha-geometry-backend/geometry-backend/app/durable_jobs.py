from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any, Callable, Optional

from .persistence.repository import DuplicateError, QuotaExceeded, Repository, Row

LOGGER = logging.getLogger("uvicorn.error.dragonfly.jobs")

JSON_COLUMNS = {"result": "result_json", "preprocessing": "preprocessing_json"}
PLAIN_COLUMNS = ("status", "progress", "stage", "stage_detail", "provider", "provider_kind", "quality_mode", "error", "error_code")
INTERRUPTED_MESSAGE = "The service restarted before this job finished. Paid reconstruction was not re-run automatically; start a new attempt."


def _loads(value: Optional[str]) -> Any:
    return json.loads(value) if value else None


class JobRecord(dict):
    """Dict view of a job row whose update() writes through to the repository."""

    def __init__(self, jobs: "DurableJobs", row: Row):
        super().__init__(
            job_id=row["id"], status=row["status"], progress=row["progress"], provider=row["provider"] or "", provider_kind=row["provider_kind"] or "",
            quality_mode=row["quality_mode"] or "STANDARD", stage=row["stage"], stage_detail=row["stage_detail"],
            preprocessing=_loads(row["preprocessing_json"]), error=row["error"], error_code=row["error_code"], result=_loads(row["result_json"]),
        )
        self._jobs = jobs
        self.kind = row["kind"]
        self.owner_id: Optional[str] = row["owner_id"]
        self.project_id: Optional[str] = row["project_id"]
        self.extra: dict = _loads(row["extra_json"]) or {}
        self.attempts = row["attempts"]

    def update(self, *args, **kwargs) -> None:  # type: ignore[override]
        changes = dict(*args, **kwargs)
        finalizer = self._jobs.finalizer
        if changes.get("status") == "done" and finalizer is not None:
            try:
                changes = {**changes, **(finalizer(self, changes) or {})}
            except Exception:
                LOGGER.exception("job_finalize_failed job_id=%s", self["job_id"])
                error_code = "provider_outcome_unknown" if self.kind == "generate" and self.get("provider_kind") == "ai" else "finalize_failed"
                message = "The AI result may have completed but could not be saved. Check your projects before starting another prediction." if error_code == "provider_outcome_unknown" else "The model could not be saved. Try again."
                changes.update(status="error", progress=100, stage="error", error=message, error_code=error_code, result=None)
        project_id = changes.pop("project_id", None)
        if project_id:
            self.project_id = project_id
        super().update(changes)
        self._jobs.persist(self, changes, project_id)


class DurableJobs:
    def __init__(self, repo: Repository, settings=None):
        self.repo = repo
        self.settings = settings
        self.finalizer: Optional[Callable[[JobRecord, dict], Optional[dict]]] = None

    def create(self, kind: str, owner_id: Optional[str], provider: str, provider_kind: str, quality_mode: str = "STANDARD",
               project_id: Optional[str] = None, extra: Optional[dict] = None, idempotency_key: Optional[str] = None,
               stage: str = "queued", stage_detail: str = "Waiting for worker.") -> tuple[JobRecord, bool]:
        scope = owner_id or "guest"
        if idempotency_key:
            existing = self.repo.find_job_by_idempotency(scope, idempotency_key)
            if existing:
                return JobRecord(self, existing), False
        now = time.time()
        row = {
            "id": uuid.uuid4().hex[:12], "owner_scope": scope, "owner_id": owner_id, "project_id": project_id, "kind": kind, "status": "queued",
            "progress": 0, "stage": stage, "stage_detail": stage_detail, "provider": provider, "provider_kind": provider_kind, "quality_mode": quality_mode,
            "extra_json": json.dumps(extra or {}), "idempotency_key": idempotency_key, "attempts": 1, "created_at": now, "updated_at": now,
        }
        try:
            limits = None
            if kind == "generate" and self.settings:
                limits = {
                    "active_user": self.settings.max_active_jobs_per_user,
                    "active_guest": self.settings.max_active_guest_jobs,
                    "daily_user": self.settings.daily_reconstructions_per_user,
                    "daily_guest": self.settings.daily_reconstructions_per_guest,
                }
            return JobRecord(self, self.repo.create_job(row, limits=limits)), True
        except QuotaExceeded:
            raise
        except DuplicateError:
            existing = self.repo.find_job_by_idempotency(scope, idempotency_key or "")
            if existing:
                return JobRecord(self, existing), False
            raise

    def get(self, job_id: str) -> Optional[JobRecord]:
        row = self.repo.get_job(job_id)
        return JobRecord(self, row) if row else None

    def __getitem__(self, job_id: str) -> JobRecord:
        record = self.get(job_id)
        if record is None:
            raise KeyError(job_id)
        return record

    def persist(self, record: JobRecord, changes: dict, project_id: Optional[str] = None) -> None:
        fields: dict[str, Any] = {name: changes[name] for name in PLAIN_COLUMNS if name in changes}
        for key, column in JSON_COLUMNS.items():
            if key in changes:
                fields[column] = json.dumps(changes[key]) if changes[key] is not None else None
        if project_id:
            fields["project_id"] = project_id
        if fields:
            self.repo.update_job(record["job_id"], fields, time.time())
        if changes.get("status") == "error":
            self.discard_source(record.extra)

    def recover_interrupted(self) -> list[str]:
        """Mark jobs left running by a previous process as failed; never re-run them (inference may be paid)."""
        recovered = []
        for row in self.repo.list_unfinished_jobs():
            self.repo.update_job(row["id"], {"status": "error", "progress": 100, "stage": "error", "stage_detail": INTERRUPTED_MESSAGE, "error": INTERRUPTED_MESSAGE, "error_code": "interrupted"}, time.time())
            extra = _loads(row["extra_json"]) or {}
            recovered.append(row["id"])
            LOGGER.warning("job_interrupted job_id=%s kind=%s", row["id"], row["kind"])
            self.discard_source(extra)
        return recovered

    def discard_source(self, extra: dict) -> None:
        source = extra.get("source_file")
        if source and self.source_cleanup:
            self.source_cleanup(source)

    source_cleanup: Optional[Callable[[str], None]] = None
