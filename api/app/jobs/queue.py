from __future__ import annotations
import json, os, time, uuid
from typing import Dict, Any, List

JOBS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "jobs_store.json"))

def _load() -> Dict[str, list]:
    if not os.path.exists(JOBS_PATH):
        return {"jobs": []}
    with open(JOBS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def _save(data: Dict[str, list]) -> None:
    with open(JOBS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _id(prefix: str = "job") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"

def enqueue_job(kind: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    data = _load()
    job = {"id": _id(), "kind": kind, "payload": payload, "status": "queued", "result": None, "created_at": int(time.time()), "updated_at": int(time.time())}
    data["jobs"].insert(0, job)
    _save(data)
    return job

def list_jobs(limit: int = 100) -> List[Dict[str, Any]]:
    return _load().get("jobs", [])[:limit]

def get_job(job_id: str) -> Dict[str, Any] | None:
    return next((j for j in _load().get("jobs", []) if j.get("id") == job_id), None)

def update_job(job_id: str, status: str, result: Dict[str, Any] | None = None) -> Dict[str, Any] | None:
    data = _load()
    for j in data.get("jobs", []):
        if j.get("id") == job_id:
            j["status"] = status
            j["result"] = result
            j["updated_at"] = int(time.time())
            _save(data)
            return j
    return None
