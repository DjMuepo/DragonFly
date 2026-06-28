from __future__ import annotations

import os
import time
import asyncio
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .services.retrieval.service import search_models
from .services.retrieval.index import ensure_schema, connect, upsert_model
from .core.schemas import LicenseInfo


# --- Types ---
LicenseStatus = Literal["OK", "RESTRICTED", "UNKNOWN"]
Novelty = Literal["COMMON", "SOMEWHAT_UNIQUE", "UNIQUE"]
JobStatus = Literal["created", "uploaded", "processing", "done", "error"]

DATA_DIR = os.environ.get("EYE_DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "data"))
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
EXPORT_DIR = os.path.join(DATA_DIR, "exports")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(EXPORT_DIR, exist_ok=True)

# Create a tiny dummy STL so the pipeline has a download.
DUMMY_STL_PATH = os.path.join(EXPORT_DIR, "dummy_cube.stl")
if not os.path.exists(DUMMY_STL_PATH):
    with open(DUMMY_STL_PATH, "w", encoding="utf-8") as f:
        f.write(
            "solid cube\n"
            "  facet normal 0 0 0\n"
            "    outer loop\n"
            "      vertex 0 0 0\n"
            "      vertex 1 0 0\n"
            "      vertex 0 1 0\n"
            "    endloop\n"
            "  endfacet\n"
            "endsolid cube\n"
        )


class CreateJobRequest(BaseModel):
    mode: Literal["snap_copy"] = "snap_copy"
    include_burst: bool = False
    query_hint: Optional[str] = None


class UploadUrls(BaseModel):
    hero_put_url: str
    burst_put_urls: List[str] = Field(default_factory=list)


class CreateJobResponse(BaseModel):
    job_id: str
    upload: UploadUrls


class MatchCandidate(BaseModel):
    id: str
    title: str
    similarity: float
    license: LicenseStatus
    preview_url: Optional[str] = None


class JobResult(BaseModel):
    matches: List[MatchCandidate] = Field(default_factory=list)
    novelty: Optional[Novelty] = None
    preview_url: Optional[str] = None
    model_download_url: Optional[str] = None


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    created_at: float
    updated_at: float
    result: Optional[JobResult] = None
    error: Optional[str] = None


@dataclass
class Job:
    job_id: str
    status: JobStatus = "created"
    created_at: float = field(default_factory=lambda: time.time())
    updated_at: float = field(default_factory=lambda: time.time())
    hero_path: Optional[str] = None
    burst_paths: List[str] = field(default_factory=list)
    query_hint: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


JOBS: Dict[str, Job] = {}

# Async job queue skeleton (replace with real queue in production)
from .core.queue import JobQueue

JOB_QUEUE: Optional[JobQueue] = None



def _base_url(req: Request) -> str:
    # Prefer explicit public base url if running behind a proxy.
    public = os.environ.get("PUBLIC_BASE_URL")
    if public:
        return public.rstrip("/")
    return str(req.base_url).rstrip("/")


async def _mark_processing_then_done(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        return
    job.status = "processing"
    job.updated_at = time.time()

    # Simulate work.
    await asyncio.sleep(1.25)

    
    # Retrieval results (MVP: in-memory seed index). Replace with vector search + license filter.
    retrieval = search_models(query_hint=(job.query_hint or "object"), allow_restricted=False, limit=6)
    matches = [
    {
        "id": c.id,
        "title": c.title,
        "similarity": float(c.similarity),
        "license": c.license.status,
        "preview_url": c.preview_url,
    }
    for c in retrieval.matches
    ]
    
    max_sim = max(m["similarity"] for m in matches) if matches else 0.0
    if max_sim >= 0.85:
        novelty: Novelty = "COMMON"
    elif max_sim >= 0.65:
        novelty = "SOMEWHAT_UNIQUE"
    else:
        novelty = "UNIQUE"

    job.result = {
        "matches": matches,
        "novelty": novelty,
        "preview_url": None,
        "model_download_url": "/exports/dummy_cube.stl",
    }

    job.status = "done"
    job.updated_at = time.time()


app = FastAPI(title="EYE Platform API", version="0.1.0")

@app.on_event("startup")
def _startup_seed_library() -> None:
    """Ensure SQLite schema exists and optionally seed a tiny open-model catalog.

    This keeps local/dev installs working out-of-the-box.
    In production, ingest a real catalog with tools/library_ingest.py.
    """
    ensure_schema()
    auto_seed = os.environ.get("EYE_AUTO_SEED_LIBRARY", "1") == "1"
    if not auto_seed:
        return

    try:
        with connect() as con:
            cur = con.execute("SELECT COUNT(1) AS n FROM models")
            n = int(cur.fetchone()["n"])
        if n > 0:
            return
    except Exception:
        # Best-effort; schema should exist.
        pass

    sample_path = os.path.join(os.path.dirname(__file__), "..", "sample_library", "models.json")
    if not os.path.exists(sample_path):
        return

    import json as _json
    from .core.schemas import LicenseInfo as _LicenseInfo

    try:
        items = _json.loads(open(sample_path, "r", encoding="utf-8").read())
        for it in items:
            lic = _LicenseInfo(**(it.get("license") or {}))
            upsert_model(
                id=it["id"],
                source=it["source"],
                title=it["title"],
                tags=it.get("tags", ""),
                license_info=lic,
                preview_url=it.get("preview_url"),
                file_url=it.get("file_url"),
            )
    except Exception:
        return


# CORS for Expo dev servers.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Serve exports
app.mount("/exports", StaticFiles(directory=EXPORT_DIR), name="exports")
app.mount("/models", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static", "models")), name="models")


@app.on_event("startup")
async def _startup():
    global JOB_QUEUE
    JOB_QUEUE = JobQueue(handler=_mark_processing_then_done)
    await JOB_QUEUE.start()



@app.get("/health")
def health():
    return {"ok": True}


@app.post("/v1/jobs", response_model=CreateJobResponse)
def create_job(req: Request, body: CreateJobRequest):
    job_id = uuid.uuid4().hex
    job = Job(job_id=job_id, query_hint=body.query_hint)
    JOBS[job_id] = job

    base = _base_url(req)
    hero_put_url = f"{base}/v1/uploads/{job_id}/hero"

    burst_put_urls: List[str] = []
    if body.include_burst:
        burst_put_urls = [f"{base}/v1/uploads/{job_id}/burst/{i}" for i in range(8)]

    return {
        "job_id": job_id,
        "upload": {
            "hero_put_url": hero_put_url,
            "burst_put_urls": burst_put_urls,
        },
    }


@app.put("/v1/uploads/{job_id}/hero")
async def upload_hero(job_id: str, request: Request, background: BackgroundTasks):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")

    content = await request.body()
    if not content:
        raise HTTPException(status_code=400, detail="empty body")

    path = os.path.join(UPLOAD_DIR, f"{job_id}_hero.jpg")
    with open(path, "wb") as f:
        f.write(content)

    job.hero_path = path
    job.status = "uploaded"
    job.updated_at = time.time()

    # Kick off processing.
    if JOB_QUEUE:
        await JOB_QUEUE.enqueue(job_id)
    else:
        background.add_task(lambda: asyncio.run(_mark_processing_then_done(job_id)))
    return {"ok": True}


@app.put("/v1/uploads/{job_id}/burst/{index}")
async def upload_burst(job_id: str, index: int, request: Request):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")

    content = await request.body()
    if not content:
        raise HTTPException(status_code=400, detail="empty body")

    path = os.path.join(UPLOAD_DIR, f"{job_id}_burst_{index}.jpg")
    with open(path, "wb") as f:
        f.write(content)

    # Ensure list size
    while len(job.burst_paths) <= index:
        job.burst_paths.append("")
    job.burst_paths[index] = path
    job.updated_at = time.time()
    return {"ok": True}


@app.get("/v1/jobs/{job_id}", response_model=JobStatusResponse)
def get_job(req: Request, job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")

    result = None
    if job.result:
        base = _base_url(req)
        # Expand relative download URLs
        r = dict(job.result)
        if r.get("model_download_url", "").startswith("/"):
            r["model_download_url"] = base + r["model_download_url"]
        result = r

    return {
        "job_id": job.job_id,
        "status": job.status,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "result": result,
        "error": job.error,
    }



from .core.schemas import RetrievalResponse, SegmentResponse
from .services.segmentation.service import _center_rect_mask, _tap_circle_mask, write_mask_png
from PIL import Image


class DraftRequest(BaseModel):
    job_id: str
    selected_model_id: Optional[str] = None  # if provided, draft from retrieved model
    edits: Optional[Dict[str, Any]] = None   # e.g. sliders/actions (MVP: ignored)

class DraftResponse(BaseModel):
    preview_url: Optional[str] = None
    model_download_url: str
    note: Optional[str] = None

@app.post("/v1/draft", response_model=DraftResponse)
def create_draft(req: Request, body: DraftRequest):
    job = JOBS.get(body.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    base = _base_url(req)
    # MVP scaffold: return dummy STL; later: if selected_model_id -> fit + edits, else -> unique recon pipeline.
    return DraftResponse(
        preview_url=None,
        model_download_url=base + "/exports/dummy_cube.stl",
        note=("draft_from_model" if body.selected_model_id else "draft_unique_placeholder")
    )


class LibrarySearchRequest(BaseModel):
    """Search the local 3D model library.

    Provide one of:
      - job_id (uses uploaded hero image for embedding-based search)
      - image_b64 (direct image search)
      - query_hint (text search)

    Switching embedding providers requires reindexing the library.
    """

    job_id: Optional[str] = None
    use_job_hero: bool = True
    image_b64: Optional[str] = None

    query_hint: Optional[str] = None
    allow_restricted: bool = False
    limit: int = 6

@app.post("/v1/library/search", response_model=RetrievalResponse)
def library_search(body: LibrarySearchRequest):
    image_bytes = None
    if body.image_b64:
        try:
            import base64
            image_bytes = base64.b64decode(body.image_b64)
        except Exception:
            raise HTTPException(status_code=400, detail="invalid image_b64")
    elif body.job_id and body.use_job_hero:
        job = JOBS.get(body.job_id)
        if job and job.hero_path and os.path.exists(job.hero_path):
            image_bytes = Path(job.hero_path).read_bytes()

    return search_models(
        query_hint=body.query_hint,
        image_bytes=image_bytes,
        allow_restricted=body.allow_restricted,
        limit=body.limit,
    )

class SegmentRequest(BaseModel):
    job_id: str

@app.post("/v1/segment", response_model=SegmentResponse)
def segment(req: Request, body: SegmentRequest):
    job = JOBS.get(body.job_id)
    if not job or not job.hero_path or not os.path.exists(job.hero_path):
        raise HTTPException(status_code=404, detail="hero image not found for job")
    img = Image.open(job.hero_path).convert("RGB")
    mask = _center_rect_mask(img.size)
    mask_path = os.path.join(UPLOAD_DIR, f"{body.job_id}_mask.png")
    write_mask_png(mask, mask_path)
    base = _base_url(req)
    return {"mask_url": f"{base}/v1/uploads/{body.job_id}/mask", "confidence": 0.55}

class RefineMaskRequest(BaseModel):
    job_id: str
    tap_x: float
    tap_y: float

@app.post("/v1/segment/refine", response_model=SegmentResponse)
def refine_mask(req: Request, body: RefineMaskRequest):
    job = JOBS.get(body.job_id)
    if not job or not job.hero_path or not os.path.exists(job.hero_path):
        raise HTTPException(status_code=404, detail="hero image not found for job")
    img = Image.open(job.hero_path).convert("RGB")
    mask = _tap_circle_mask(img.size, body.tap_x, body.tap_y)
    mask_path = os.path.join(UPLOAD_DIR, f"{body.job_id}_mask.png")
    write_mask_png(mask, mask_path)
    base = _base_url(req)
    return {"mask_url": f"{base}/v1/uploads/{body.job_id}/mask", "confidence": 0.65}

@app.get("/v1/uploads/{job_id}/mask")
def get_mask(job_id: str):
    mask_path = os.path.join(UPLOAD_DIR, f"{job_id}_mask.png")
    if not os.path.exists(mask_path):
        raise HTTPException(status_code=404, detail="mask not found")
    with open(mask_path, "rb") as f:
        return Response(content=f.read(), media_type="image/png")


@app.get("/v1/sources")
def list_sources():
    """List configured remote sources. (In v7 these are metadata-only stubs; replace connectors with real API clients when credentials/terms allow.)"""
    return {
        "sources": [
            {"id": "thingiverse", "mode": "api-or-stub"},
            {"id": "nih3d", "mode": "metadata"},
            {"id": "printables", "mode": "metadata-only"},
            {"id": "thangs", "mode": "metadata-only"},
            {"id": "grabcad", "mode": "metadata-only"},
        ]
    }


from app.services.structural.analyzer import analyze_from_simple_params, apply_strengthen

class StructuralAnalyzeRequest(BaseModel):
    # simple params from client edits
    params: dict = {}

class StructuralStrengthenRequest(BaseModel):
    params: dict = {}

@app.post("/v1/structural/analyze")
def structural_analyze(req: StructuralAnalyzeRequest):
    rep = analyze_from_simple_params(req.params or {})
    return rep.__dict__

@app.post("/v1/structural/strengthen")
def structural_strengthen(req: StructuralStrengthenRequest):
    params = dict(req.params or {})
    params2 = apply_strengthen(params)
    rep = analyze_from_simple_params(params2)
    return {"params": params2, "report": rep.__dict__}

from app.services.telemetry.logger import log_event, ensure_schema as ensure_events_schema


@app.post("/v1/events/log")
def events_log(req: dict):
    # minimal payload contract to keep mobile client simple
    event = req.get("event") or "unknown"
    log_event(
        event=event,
        session_id=req.get("session_id"),
        user_id=req.get("user_id"),
        job_id=req.get("job_id"),
        model_id=req.get("model_id"),
        payload=req.get("payload") or {},
    )
    return {"ok": True}

@app.get("/v1/events/export")
def events_export(limit: int = 1000):
    """Export most recent events (for ML dataset building)."""
    ensure_events_schema()
    import sqlite3, os, json
    from app.services.telemetry.logger import DB_PATH
    if not os.path.exists(DB_PATH):
        return {"events": []}
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    rows = con.execute("SELECT * FROM events ORDER BY ts DESC LIMIT ?", (limit,)).fetchall()
    out = []
    for r in rows:
        out.append({
            "ts": r["ts"],
            "session_id": r["session_id"],
            "user_id": r["user_id"],
            "event": r["event"],
            "job_id": r["job_id"],
            "model_id": r["model_id"],
            "payload": json.loads(r["payload_json"] or "{}"),
        })
    return {"events": out}


from fastapi import UploadFile, File
from fastapi.responses import JSONResponse
import hashlib
import os
from datetime import datetime

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/v1/review/photo")
async def upload_review_photo(file: UploadFile = File(...)):
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        return JSONResponse({"error": "File too large (5MB max)"}, status_code=400)

    h = hashlib.sha256(content).hexdigest()[:16]
    ext = os.path.splitext(file.filename or "")[1] or ".jpg"
    name = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{h}{ext}"
    path = os.path.join(UPLOAD_DIR, name)

    with open(path, "wb") as f:
        f.write(content)

    return {"ok": True, "filename": name}

from app.services.structural.analyzer import ensure_policy_trained


@app.post("/v1/simulate/basic")
def simulate_basic(req: dict):
    """Pro feature scaffold: returns deflection estimate + risk.
    `mode` presets: 'custom' | 'drop' | 'side_load' | 'twist'
    """
    p = req.get("params") or {}
    mode = (req.get("mode") or "custom").lower()
    thickness = float(p.get("thickness", 1.0))
    cantilever = float(p.get("cantilever", 0.0))
    aspect = float(p.get("aspect_ratio", 1.0))
    force = float(req.get("force", 1.0))

    # Preset shaping
    load_type = "Multi-axis"
    if mode == "drop":
        # impulse through z; higher effective force
        force = max(force, 3.0)
        load_type = "Compression"
        k = 1.15
    elif mode == "side_load":
        force = max(force, 2.0)
        load_type = "Shear"
        k = 1.0 + cantilever * 0.35
    elif mode == "twist":
        force = max(force, 2.0)
        load_type = "Torsion"
        k = 1.05 + (aspect-1.0) * 0.25
    else:
        k = 1.0

    # simple deflection proxy: higher cantilever/aspect and lower thickness => more deflection
    geom = (cantilever + max(0.0, aspect-1.0)) * k
    deflection = (force * geom) / max(0.2, thickness)
    deflection_score = max(0.0, min(100.0, deflection * 20.0))
    risk = "LOW" if deflection_score < 30 else "MED" if deflection_score < 65 else "HIGH"

    vec = {"x": 0.0, "y": 0.0, "z": 0.0}
    if mode == "drop":
        vec["z"] = -force
    elif mode == "side_load":
        vec["x"] = force
    elif mode == "twist":
        vec["y"] = force
    else:
        vec["x"] = force

    return {"deflection_score": deflection_score, "risk": risk, "force": force, "mode": mode, "load_type": load_type, "force_vector": vec}

from app.services.vector.faiss_index import build_faiss_index


@app.on_event("startup")
def _startup_build_faiss():
    try:
        build_faiss_index()
    except Exception:
        pass


from app.vision.classifier import classify_image_bytes
from app.vision.segment import simple_center_mask, apply_mask_preview
from app.vision.retrieval import retrieve_from_image_bytes, retrieve_from_text
from app.vision.draft_generator import generate_basic_draft

@app.post("/v1/vision/classify")
async def vision_classify(file: UploadFile = File(...)):
    data = await file.read()
    return classify_image_bytes(data)

@app.post("/v1/vision/segment")
async def vision_segment(file: UploadFile = File(...)):
    data = await file.read()
    mask = simple_center_mask(data)
    preview = apply_mask_preview(data, mask)

    # save preview/mask for inspection
    import hashlib, os
    h = hashlib.sha256(data).hexdigest()[:12]
    mask_name = f"mask_{h}.png"
    prev_name = f"preview_{h}.png"
    with open(os.path.join(UPLOAD_DIR, mask_name), "wb") as f:
        f.write(mask)
    with open(os.path.join(UPLOAD_DIR, prev_name), "wb") as f:
        f.write(preview)

    return {
        "ok": True,
        "mask_filename": mask_name,
        "preview_filename": prev_name,
    }

@app.post("/v1/vision/retrieve")
async def vision_retrieve(file: UploadFile = File(...), allow_restricted: bool = False, limit: int = 8):
    data = await file.read()
    res = retrieve_from_image_bytes(data, allow_restricted=allow_restricted, limit=limit)
    return res.model_dump()

@app.get("/v1/vision/retrieve_text")
def vision_retrieve_text(q: str, allow_restricted: bool = False, limit: int = 8):
    res = retrieve_from_text(q, allow_restricted=allow_restricted, limit=limit)
    return res.model_dump()

@app.post("/v1/vision/draft")
async def vision_draft(file: UploadFile = File(...)):
    data = await file.read()
    cls = classify_image_bytes(data)
    mask = simple_center_mask(data)
    draft = generate_basic_draft(mask, object_family=cls.get("object_family", "object"))
    return {
        "classification": cls,
        "draft": draft,
    }


@app.post("/v1/vision/classify_and_retrieve")
async def vision_classify_and_retrieve(file: UploadFile = File(...), allow_restricted: bool = False, limit: int = 8):
    data = await file.read()
    cls = classify_image_bytes(data)
    img_res = retrieve_from_image_bytes(data, allow_restricted=allow_restricted, limit=limit)
    txt_res = retrieve_from_text(cls.get("object_family", ""), allow_restricted=allow_restricted, limit=max(3, limit // 2))

    return {
        "classification": cls,
        "image_matches": img_res.model_dump(),
        "text_matches": txt_res.model_dump(),
    }

from app.vision.preview_generator import generate_preview_png


@app.post("/v1/vision/preview")
async def vision_preview(file: UploadFile = File(...)):
    data = await file.read()
    cls = classify_image_bytes(data)
    mask = simple_center_mask(data)
    draft = generate_basic_draft(mask, object_family=cls.get("object_family", "object"))
    preview = generate_preview_png(data, mask, draft)

    import hashlib, os
    h = hashlib.sha256(data).hexdigest()[:12]
    prev_name = f"draft_preview_{h}.png"
    with open(os.path.join(UPLOAD_DIR, prev_name), "wb") as f:
        f.write(preview)

    return {
        "classification": cls,
        "draft": draft,
        "preview_filename": prev_name,
        "preview_url": f"/uploads/{prev_name}",
    }


try:
    app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
except Exception:
    pass


@app.post("/v1/vision/geometry_preview")
async def vision_geometry_preview(file: UploadFile = File(...)):
    data = await file.read()
    cls = classify_image_bytes(data)
    mask = simple_center_mask(data)
    draft = generate_basic_draft(mask, object_family=cls.get("object_family", "object"))

    family = (cls.get("object_family") or "object").lower()
    shape = "box"
    if family in ("handle", "grip"):
        shape = "capsule"
    elif family in ("toy", "phone stand"):
        shape = "wedge"
    else:
        shape = "box"

    bbox = draft.get("bbox") or {}
    w = max(1, (bbox.get("x1", 100) - bbox.get("x0", 0)))
    h = max(1, (bbox.get("y1", 100) - bbox.get("y0", 0)))
    aspect = float(draft.get("aspect_ratio", 1.0) or 1.0)
    depth_ratio = float(draft.get("estimated_depth_ratio", 0.2) or 0.2)

    base_w = 1.0
    base_h = max(0.35, min(1.8, 1.0 / max(0.5, aspect)))
    base_d = max(0.15, min(1.2, depth_ratio * 2.5))

    return {
        "classification": cls,
        "draft": draft,
        "geometry": {
            "shape": shape,
            "width": round(base_w, 3),
            "height": round(base_h, 3),
            "depth": round(base_d, 3),
            "notes": [
                "Lightweight generated geometry preview.",
                "Final mesh generation comes later."
            ]
        }
    }

from app.vision.depth_estimator import estimate_depth_map
from app.vision.parametric_draft import build_parametric_draft

@app.post("/v1/vision/reconstruct")
async def vision_reconstruct(file: UploadFile = File(...)):
    data = await file.read()
    cls = classify_image_bytes(data)
    family = (cls.get("object_family") or "object").lower()
    supported = family in ["bracket", "hook", "clip", "handle", "enclosure", "adapter"]
    if not supported:
        family = "bracket" if ("part" in family or "mechanical" in family) else "hook" if family == "connector" else "enclosure" if family == "container" else family
        supported = family in ["bracket", "hook", "clip", "handle", "enclosure", "adapter"]
    mask = simple_center_mask(data)
    draft = generate_basic_draft(mask, object_family=family)
    depth_meta = estimate_depth_map(data)
    parametric = build_parametric_draft(
        family=family,
        bbox=draft.get("bbox") or {},
        aspect_ratio=float(draft.get("aspect_ratio", 1.0) or 1.0),
        depth_ratio=float(draft.get("estimated_depth_ratio", 0.2) or 0.2),
        depth_meta=depth_meta,
    )
    return {"classification": cls, "supported_family": supported, "family": family, "parametric_draft": parametric}


@app.post("/v1/vision/classify_multi")
async def vision_classify_multi(files: list[UploadFile] = File(...)):
    results = []
    family_counts = {}
    conf_by_family = {}
    for f in files[:6]:
        data = await f.read()
        cls = classify_image_bytes(data)
        fam = (cls.get("object_family") or "object").lower()
        conf = float(cls.get("confidence") or 0.0)
        family_counts[fam] = family_counts.get(fam, 0) + 1
        conf_by_family.setdefault(fam, []).append(conf)
        results.append(cls)

    if not family_counts:
        return {"object_family": "object", "confidence": 0.0, "top": []}

    best_family = sorted(family_counts.items(), key=lambda kv: (kv[1], sum(conf_by_family.get(kv[0], []))), reverse=True)[0][0]
    avg_conf = sum(conf_by_family.get(best_family, [0.0])) / max(1, len(conf_by_family.get(best_family, [])))
    return {
        "object_family": best_family,
        "confidence": avg_conf,
        "top": [{"label": k, "confidence": sum(v)/max(1,len(v))} for k, v in sorted(conf_by_family.items(), key=lambda kv: sum(kv[1]), reverse=True)[:5]],
        "views_used": len(results),
    }

@app.post("/v1/vision/reconstruct_multi")
async def vision_reconstruct_multi(files: list[UploadFile] = File(...)):
    datas = []
    for f in files[:6]:
        datas.append(await f.read())
    if not datas:
        return {"error": "no files"}
    # classify by consensus; draft from hero (first image) but improve confidence and depth slightly using extra views
    family_counts = {}
    conf_by_family = {}
    for data in datas:
        cls = classify_image_bytes(data)
        fam = (cls.get("object_family") or "object").lower()
        conf = float(cls.get("confidence") or 0.0)
        family_counts[fam] = family_counts.get(fam, 0) + 1
        conf_by_family.setdefault(fam, []).append(conf)

    family = sorted(family_counts.items(), key=lambda kv: (kv[1], sum(conf_by_family.get(kv[0], []))), reverse=True)[0][0]
    supported = family in ["bracket", "hook", "clip", "handle", "enclosure", "adapter"]
    if not supported:
        family = "bracket" if ("part" in family or "mechanical" in family) else "hook" if family == "connector" else "enclosure" if family == "container" else family
        supported = family in ["bracket", "hook", "clip", "handle", "enclosure", "adapter"]

    hero = datas[0]
    mask = simple_center_mask(hero)
    draft = generate_basic_draft(mask, object_family=family)

    # aggregate lightweight depth info from all views
    from app.vision.depth_estimator import estimate_depth_map
    depths = [estimate_depth_map(d) for d in datas]
    depth_center = sum(d.get("depth_center", 0.0) for d in depths) / max(1, len(depths))
    depth_edges = sum(d.get("depth_edges", 0.0) for d in depths) / max(1, len(depths))
    depth_contrast = sum(d.get("depth_contrast", 0.0) for d in depths) / max(1, len(depths))
    depth_meta = {
        "depth_center": round(depth_center, 4),
        "depth_edges": round(depth_edges, 4),
        "depth_contrast": round(depth_contrast, 4),
        "confidence": 0.58,
        "notes": ["Guided multi-angle depth estimate.", f"{len(datas)} views fused lightly."],
    }

    from app.vision.parametric_draft import build_parametric_draft
    parametric = build_parametric_draft(
        family=family,
        bbox=draft.get("bbox") or {},
        aspect_ratio=float(draft.get("aspect_ratio", 1.0) or 1.0),
        depth_ratio=float(draft.get("estimated_depth_ratio", 0.2) or 0.2) * 1.08,
        depth_meta=depth_meta,
    )
    parametric["confidence"] = min(0.82, float(parametric.get("confidence", 0.5)) + 0.12)

    parametric = adapt_parametric_draft(parametric)
    return {
        "classification": {"object_family": family, "confidence": min(0.95, sum(conf_by_family.get(family, [0.0]))/max(1,len(conf_by_family.get(family, []))) + 0.08)},
        "supported_family": supported,
        "family": family,
        "parametric_draft": parametric,
        "views_used": len(datas),
        "learning_applied": True,
    }

@app.post("/v1/vision/retrieve_multi")
async def vision_retrieve_multi(files: list[UploadFile] = File(...), allow_restricted: bool = False, limit: int = 8):
    datas = []
    for f in files[:6]:
        datas.append(await f.read())
    if not datas:
        return {"matches": [], "novelty": "UNIQUE", "best_match": None, "max_similarity": 0.0}

    # Use first image retrieval for now; functional option with multi-capture classification consistency.
    res = retrieve_from_image_bytes(datas[0], allow_restricted=allow_restricted, limit=limit)
    out = res.model_dump()
    out["views_used"] = len(datas)
    return out

from app.vision.stl_exporter import export_parametric_stl
from app.vision.printability import analyze_printability

@app.post("/v1/vision/export_stl")
async def vision_export_stl(payload: dict):
    import os, time
    parametric = payload.get("parametric_draft") or {}
    family = (parametric.get("family") or "object").lower()
    filename = f"draft_{family}_{int(time.time())}.stl"
    out_path = os.path.join(UPLOAD_DIR, filename)
    meta = export_parametric_stl(parametric, out_path)
    return {"ok": True, "filename": filename, "download_url": f"/uploads/{filename}", "meta": meta}


@app.post("/v1/vision/printability")
async def vision_printability(payload: dict):
    parametric = payload.get("parametric_draft") or {}
    return analyze_printability(parametric)

from app.services.printers import find_nearby_printers, submit_print_job, list_nodes, set_node_status


@app.post("/v1/printers/nearby")
async def printers_nearby(payload: dict):
    lat = float(payload.get("lat"))
    lon = float(payload.get("lon"))
    material = payload.get("material")
    return {"printers": find_nearby_printers(lat, lon, material)}

@app.post("/v1/printers/submit")
async def printers_submit(payload: dict):
    printer_id = payload.get("printer_id")
    return submit_print_job(printer_id, payload)

from app.services.sharing import publish_design, list_public_designs, get_design, seed_if_empty


@app.get("/v1/designs")
async def designs_list():
    seed_if_empty()
    return {"designs": list_public_designs()}

@app.get("/v1/designs/{slug}")
async def designs_get(slug: str):
    seed_if_empty()
    d = get_design(slug)
    if not d:
        return {"ok": False, "error": "not_found"}
    return {"ok": True, "design": d}

@app.post("/v1/designs/publish")
async def designs_publish(payload: dict):
    d = publish_design(payload)
    return {"ok": True, "design": d, "share_url": f"/design/{d['slug']}", "app_deep_link": f"eyeplatform://design/{d['slug']}"}

from app.services.auth import signup, login, get_user_by_token, list_user_designs
from app.services.sharing import publish_design, list_public_designs, get_design, seed_if_empty, like_design, list_creator_designs

@app.post("/v1/auth/signup")
async def auth_signup(payload: dict):
    try:
        return {"ok": True, **signup(payload.get("email",""), payload.get("password",""), payload.get("name",""), payload.get("interests") or [], payload.get("skill_level") or "beginner")}
    except ValueError as e:
        return {"ok": False, "error": str(e)}

@app.post("/v1/auth/login")
async def auth_login(payload: dict):
    try:
        return {"ok": True, **login(payload.get("email",""), payload.get("password",""))}
    except ValueError as e:
        return {"ok": False, "error": str(e)}

@app.get("/v1/me")
async def auth_me(token: str):
    user = get_user_by_token(token)
    if not user:
        return {"ok": False, "error": "invalid_token"}
    return {"ok": True, "user": user}

@app.get("/v1/my-designs")
async def my_designs(token: str):
    user = get_user_by_token(token)
    if not user:
        return {"ok": False, "error": "invalid_token"}
    return {"ok": True, "designs": list_user_designs(user["id"])}

@app.post("/v1/designs/{slug}/like")
async def designs_like(slug: str):
    d = like_design(slug)
    if not d:
        return {"ok": False, "error": "not_found"}
    return {"ok": True, "design": d}


@app.get("/v1/creators/{creator}")
async def creator_designs(creator: str):
    seed_if_empty()
    return {"ok": True, "creator": creator, "designs": list_creator_designs(creator)}

from app.training.event_store import append_event, read_events
from app.training.aggregator import aggregate_events
from app.training.feature_store import load_features
from app.training.adapters import adapt_parametric_draft

@app.post("/v1/training/event")
async def training_event(payload: dict):
    return {"ok": True, "event": append_event(payload)}

@app.get("/v1/training/events")
async def training_events(limit: int = 200):
    return {"ok": True, "events": read_events(limit=limit)}

@app.post("/v1/training/aggregate")
async def training_aggregate(payload: dict | None = None):
    limit = int((payload or {}).get("limit", 5000))
    features = aggregate_events(limit=limit)
    return {"ok": True, "features": features}

@app.get("/v1/training/features")
async def training_features():
    return {"ok": True, "features": load_features()}

@app.post("/v1/training/adapt")
async def training_adapt(payload: dict):
    parametric = payload.get("parametric_draft") or {}
    return {"ok": True, "parametric_draft": adapt_parametric_draft(parametric)}


@app.post("/v1/vision/apply_learned_defaults")
async def vision_apply_learned_defaults(payload: dict):
    parametric = payload.get("parametric_draft") or {}
    adapted = adapt_parametric_draft(parametric)
    return {"ok": True, "parametric_draft": adapted}

from app.preview.preview_service import generate_preview
from app.remix.remix_service import remix_design


@app.post("/v1/designs/preview")
async def create_preview(payload: dict):
    slug = payload.get("slug")
    title = payload.get("title","Design")
    return {"ok": True, "preview": generate_preview(slug, title)}

@app.post("/v1/designs/remix")
async def remix_endpoint(payload: dict):
    original = payload.get("design") or {}
    creator = payload.get("creator","anonymous")
    new_design = remix_design(original, creator)
    return {"ok": True, "design": new_design}

from app.preview.preview_service import upload_preview_local


@app.post("/v1/designs/{slug}/host-preview")
async def host_design_preview(slug: str):
    try:
        return upload_preview_local(slug)
    except FileNotFoundError:
        return {"ok": False, "error": "preview_not_found"}

from app.jobs.queue import enqueue_job, list_jobs, get_job, update_job

from app.workers.executor import run_once
from app.db.postgres_adapter import healthcheck as postgres_healthcheck


@app.post("/v1/jobs/run-once")
async def jobs_run_once(payload: dict | None = None):
    limit = int((payload or {}).get("limit", 25))
    return run_once(limit=limit)

@app.get("/v1/db/postgres-health")
async def db_postgres_health():
    return postgres_healthcheck()


@app.get("/readiness")
async def readiness():
    return {"ok": True, "service": "eye-platform-api", "ready": True}

from app.services.challenges import list_challenges, get_challenge, submit_challenge_entry, get_leaderboard, list_submissions


@app.get("/v1/challenges")
async def challenges_list():
    return {"ok": True, "challenges": list_challenges()}

@app.get("/v1/challenges/{challenge_id}")
async def challenges_get(challenge_id: str):
    item = get_challenge(challenge_id)
    if not item:
        return {"ok": False, "error": "not_found"}
    return {"ok": True, "challenge": item, "submissions": list_submissions(challenge_id), "leaderboard": get_leaderboard(challenge_id)}

@app.post("/v1/challenges/{challenge_id}/submit")
async def challenges_submit(challenge_id: str, payload: dict):
    if not get_challenge(challenge_id):
        return {"ok": False, "error": "not_found"}
    return {"ok": True, "submission": submit_challenge_entry(challenge_id, payload)}

from app.services.world_map import add_object,list_objects
from app.services.collab_scan import submit_scan,get_scans
from app.services.scan_missions import list_missions

@app.get("/v1/world/objects")
async def world_objects():
    return {"ok":True,"objects":list_objects()}

@app.post("/v1/world/add_object")
async def world_add_object(payload:dict):
    return {"ok":True,"object":add_object(payload.get("lat"),payload.get("lon"),payload.get("title"),payload.get("creator","anon"))}

@app.get("/v1/world/missions")
async def world_missions():
    return {"ok":True,"missions":list_missions()}

@app.post("/v1/world/collab_scan")
async def world_collab_scan(payload:dict):
    return {"ok":True,"scan":submit_scan(payload["object_id"],payload["angle"],payload.get("user","anon"))}

@app.get("/v1/world/scans/{object_id}")
async def world_scans(object_id:str):
    return {"ok":True,"scans":get_scans(object_id)}

from app.services.live_detection import process_live_detection


@app.post("/v1/vision/live-detect")
async def vision_live_detect(payload: dict):
    return {"ok": True, "result": process_live_detection(payload)}

from app.services.fix_object import generate_fix_plan


@app.post("/v1/fix-object/plan")
async def fix_object_plan(payload: dict):
    return generate_fix_plan(payload)

from app.services.camera_router import route_camera_action


@app.post("/v1/camera/route")
async def camera_route(payload: dict):
    return route_camera_action(payload)

from app.services.discovery_radar import build_radar


@app.post("/v1/radar/discovery")
async def radar_discovery(payload: dict):
    return build_radar(payload)

from app.services.ar_placement import generate_ar_placement_plan


@app.post("/v1/ar/placement-plan")
async def ar_placement_plan(payload: dict):
    return generate_ar_placement_plan(payload)

from app.services.object_dna_store import create_record, list_records, get_record, update_record
from app.services.object_dna_flow_bridge import write_from_scan, write_from_fix, write_from_ar, write_print_outcome, append_user_edit


@app.post('/v1/object-dna')
async def object_dna_create(payload: dict):
    return {'ok': True, 'record': create_record(payload)}

@app.get('/v1/object-dna')
async def object_dna_list(limit: int = 100):
    return {'ok': True, 'records': list_records(limit=limit)}

@app.get('/v1/object-dna/{record_id}')
async def object_dna_get(record_id: str):
    record = get_record(record_id)
    if not record: return {'ok': False, 'error': 'not_found'}
    return {'ok': True, 'record': record}

@app.post('/v1/object-dna/{record_id}')
async def object_dna_update(record_id: str, payload: dict):
    record = update_record(record_id, payload)
    if not record: return {'ok': False, 'error': 'not_found'}
    return {'ok': True, 'record': record}


@app.post('/v1/object-dna/flows/scan')
async def object_dna_flow_scan(payload: dict):
    return {'ok': True, 'record': write_from_scan(payload)}

@app.post('/v1/object-dna/flows/fix')
async def object_dna_flow_fix(payload: dict):
    return {'ok': True, 'record': write_from_fix(payload)}

@app.post('/v1/object-dna/flows/ar')
async def object_dna_flow_ar(payload: dict):
    return {'ok': True, 'record': write_from_ar(payload)}

@app.post('/v1/object-dna/flows/print')
async def object_dna_flow_print(payload: dict):
    record = write_print_outcome(payload)
    if not record: return {'ok': False, 'error': 'missing_record_id'}
    return {'ok': True, 'record': record}

@app.post('/v1/object-dna/flows/edit')
async def object_dna_flow_edit(payload: dict):
    record = append_user_edit(payload)
    if not record: return {'ok': False, 'error': 'missing_record_id'}
    return {'ok': True, 'record': record}


from app.services.flow_auto_hooks import auto_hook_scan_accept, auto_hook_fix_accept, auto_hook_ar_confirm, auto_hook_print_complete, auto_hook_user_edit

@app.post("/v1/flows/scan/accept")
async def flows_scan_accept(payload: dict):
    return {"ok": True, "record": auto_hook_scan_accept(payload)}

@app.post("/v1/flows/fix/accept")
async def flows_fix_accept(payload: dict):
    return {"ok": True, "record": auto_hook_fix_accept(payload)}

@app.post("/v1/flows/ar/confirm")
async def flows_ar_confirm(payload: dict):
    return {"ok": True, "record": auto_hook_ar_confirm(payload)}

@app.post("/v1/flows/print/complete")
async def flows_print_complete(payload: dict):
    return {"ok": True, "record": auto_hook_print_complete(payload)}

@app.post("/v1/flows/edit/append")
async def flows_edit_append(payload: dict):
    return {"ok": True, "record": auto_hook_user_edit(payload)}

from app.services.ai_learning import summarize_learning


@app.get("/v1/ai/learning-summary")
async def ai_learning_summary(limit: int = 500):
    return summarize_learning(limit=limit)


from app.services.subscription_gate import require_subscription

@app.post("/v1/subscription/auto-save-check")
async def subscription_auto_save_check(payload: dict):
    return require_subscription(payload)

from app.services.feature_access import list_features, check_access, update_feature, set_user_override, get_audit_log


@app.get("/v1/admin/features")
async def admin_features():
    return {"ok": True, "data": list_features()}

@app.post("/v1/admin/features/check")
async def admin_features_check(payload: dict):
    return check_access(payload)

@app.post("/v1/admin/features/update")
async def admin_features_update(payload: dict):
    return update_feature(payload)

@app.post("/v1/admin/features/override")
async def admin_features_override(payload: dict):
    return set_user_override(payload)

@app.get("/v1/admin/features/audit")
async def admin_features_audit(limit: int = 100):
    return {"ok": True, "audit_log": get_audit_log(limit=limit)}


from app.services.behavior_engine import create_temp_session, ghost_save, exit_warning, recover_session, record_print_success, get_events

@app.post("/v1/behavior/session/create")
async def behavior_session_create(payload: dict):
    return create_temp_session(payload)

@app.post("/v1/behavior/ghost-save")
async def behavior_ghost_save(payload: dict):
    return ghost_save(payload)

@app.post("/v1/behavior/exit-warning")
async def behavior_exit_warning(payload: dict):
    return exit_warning(payload)

@app.post("/v1/behavior/recover")
async def behavior_recover(payload: dict):
    return recover_session(payload)

@app.post("/v1/behavior/print-success")
async def behavior_print_success(payload: dict):
    return record_print_success(payload)

@app.get("/v1/behavior/events")
async def behavior_events(limit: int = 100):
    return {"ok": True, "events": get_events(limit=limit)}


from app.services.invite_registry import create_invite, validate_invite, redeem_invite, disable_invite, list_invites

@app.get("/v1/invites")
async def invites_list():
    return {"ok": True, "data": list_invites()}

@app.post("/v1/invites/create")
async def invites_create(payload: dict):
    return create_invite(payload)

@app.post("/v1/invites/validate")
async def invites_validate(payload: dict):
    return validate_invite(payload)

@app.post("/v1/invites/redeem")
async def invites_redeem(payload: dict):
    return redeem_invite(payload)

@app.post("/v1/invites/disable")
async def invites_disable(payload: dict):
    return disable_invite(payload)


from app.services.share_funnel import create_share_link, list_share_links

@app.post("/v1/share/create")
async def share_create(payload: dict):
    return create_share_link(payload)

@app.get("/v1/share/list")
async def share_list(limit: int = 100):
    return list_share_links(limit=limit)
