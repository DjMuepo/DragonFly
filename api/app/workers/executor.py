from __future__ import annotations
from typing import Dict, Any
from app.jobs.queue import list_jobs, update_job
from app.preview.preview_service import generate_preview

def process_job(job: Dict[str, Any]) -> Dict[str, Any]:
    kind = job.get("kind")
    payload = job.get("payload") or {}
    if kind == "preview_render":
        slug = payload.get("slug") or "job-preview"
        title = payload.get("title") or "Generated Preview"
        family = payload.get("family") or "object"
        creator = payload.get("creator") or "Anonymous"
        result = generate_preview(slug, title, family, creator)
        return {"ok": True, "kind": kind, "result": result}
    if kind == "training_aggregate":
        return {"ok": True, "kind": kind, "result": {"message": "aggregation placeholder"}}
    return {"ok": True, "kind": kind, "result": {"message": "no-op job"}}

def run_once(limit: int = 25) -> Dict[str, Any]:
    jobs = list_jobs(limit=limit)
    processed = 0
    for job in jobs:
        if job.get("status") != "queued":
            continue
        update_job(job["id"], "running", {"started": True})
        out = process_job(job)
        update_job(job["id"], "done", out)
        processed += 1
    return {"ok": True, "processed": processed}
