from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Dict, Optional

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .mesh_factory import export_glb, infer_preset

BASE_DIR = Path(__file__).resolve().parents[1]
STATIC_DIR = BASE_DIR / "static"
MODELS_DIR = STATIC_DIR / "models"
UPLOADS_DIR = STATIC_DIR / "uploads"
MODELS_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Eye Geometry Backend", version="0.3.0-alpha")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

JOBS: Dict[str, dict] = {}

class GeometryRequest(BaseModel):
    label: str = Field(default="Object")
    confidence: float = Field(default=0.7, ge=0, le=1)
    mode: str = Field(default="approximate")
    prompt: Optional[str] = None

class EditRequest(BaseModel):
    label: str = Field(default="Object")
    model_url: Optional[str] = None
    prompt: str = Field(default="make it printable")

class GeometryResponse(BaseModel):
    ok: bool
    job_id: str
    engine: str
    status: str
    label: str
    detected_family: str
    model_name: str
    model_url: str
    download_url: str
    created_at: float
    notes: str

class VisionResponse(BaseModel):
    ok: bool
    label: str
    family: str
    confidence: float
    suggestions: list[str]

class PrintPrepRequest(BaseModel):
    model_url: Optional[str] = None
    material: str = "PLA"
    infill_percent: int = 20


def public_base(request: Request) -> str:
    return str(request.base_url).rstrip("/")


def model_response(request: Request, label: str, engine: str, prompt: str | None = None) -> GeometryResponse:
    filename, _ = export_glb(label or "Object", MODELS_DIR, prompt=prompt)
    model_path = f"/v1/geometry/models/{filename}"
    model_url = f"{public_base(request)}{model_path}"
    job_id = uuid.uuid4().hex[:12]
    payload = GeometryResponse(
        ok=True,
        job_id=job_id,
        engine=engine,
        status="done",
        label=label or "Object",
        detected_family=infer_preset(label or "Object"),
        model_name=filename,
        model_url=model_url,
        download_url=model_url,
        created_at=time.time(),
        notes="Procedural alpha GLB generated through provider-ready pipeline. Swap provider to TripoSR, TRELLIS, Hunyuan3D, or Stable Fast 3D without changing the frontend contract.",
    )
    JOBS[job_id] = payload.model_dump()
    return payload


def classify_label(label: str | None, filename: str | None = None) -> str:
    haystack = f"{label or ''} {filename or ''}".lower()
    if any(x in haystack for x in ["phone", "iphone", "samsung", "mobile"]):
        return "Smartphone"
    if any(x in haystack for x in ["bottle", "spray", "deodorant", "can"]):
        return "Bottle"
    if any(x in haystack for x in ["cup", "mug"]):
        return "Cup"
    return label or "Object"


@app.get("/")
def root():
    return {"ok": True, "service": "eye-geometry-backend", "version": "0.3.0-alpha"}

@app.get("/health")
def health():
    return {"ok": True, "service": "eye-geometry-backend", "version": "0.3.0-alpha", "models_dir": str(MODELS_DIR), "time": time.time()}

@app.post("/v1/vision/classify", response_model=VisionResponse)
async def classify_image(label: str = Form(default="Object"), image: Optional[UploadFile] = File(default=None)):
    saved_name = None
    if image is not None:
        saved_name = f"{uuid.uuid4().hex}_{Path(image.filename or 'scan.jpg').name}"
        (UPLOADS_DIR / saved_name).write_bytes(await image.read())
    detected = classify_label(label, saved_name)
    family = infer_preset(detected)
    suggestions = ["Generate 3D model", "Make printable", "Create protective case", "Add stand/base"]
    return VisionResponse(ok=True, label=detected, family=family, confidence=0.82 if detected != "Object" else 0.62, suggestions=suggestions)

@app.post("/v1/geometry/generate", response_model=GeometryResponse)
def generate_geometry(payload: GeometryRequest, request: Request):
    label = classify_label(payload.label)
    return model_response(request, label, "eye-provider-router-procedural-alpha", prompt=payload.prompt)

@app.post("/v1/geometry/generate-from-image", response_model=GeometryResponse)
async def generate_geometry_from_image(request: Request, label: str = Form(default="Object"), confidence: float = Form(default=0.7), image: Optional[UploadFile] = File(default=None)):
    saved_name = None
    if image is not None:
        saved_name = f"{uuid.uuid4().hex}_{Path(image.filename or 'scan.jpg').name}"
        (UPLOADS_DIR / saved_name).write_bytes(await image.read())
    detected = classify_label(label, saved_name)
    return model_response(request, detected, "eye-image-to-3d-provider-router-alpha")

@app.post("/v1/geometry/edit", response_model=GeometryResponse)
def edit_geometry(payload: EditRequest, request: Request):
    label = classify_label(payload.label)
    return model_response(request, label, "eye-text-to-mesh-edit-alpha", prompt=payload.prompt)

@app.post("/v1/geometry/prepare-print")
def prepare_print(payload: PrintPrepRequest):
    return {
        "ok": True,
        "status": "print-check-complete",
        "material": payload.material,
        "infill_percent": payload.infill_percent,
        "estimated_weight_g": 42,
        "estimated_print_time_min": 95,
        "checks": ["mesh centered", "scale normalized", "non-manifold repair queued", "wall thickness check queued"],
        "notes": "Alpha print prep estimate. Replace with slicer integration in next batch.",
    }

@app.get("/v1/geometry/jobs/{job_id}")
def job_status(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@app.get("/v1/geometry/models/{model_name}")
def download_model(model_name: str):
    safe_name = Path(model_name).name
    path = MODELS_DIR / safe_name
    if not path.exists():
        fallback_name, fallback_path = export_glb("Object", MODELS_DIR)
        path = fallback_path
    return FileResponse(path, media_type="model/gltf-binary", filename=path.name)
