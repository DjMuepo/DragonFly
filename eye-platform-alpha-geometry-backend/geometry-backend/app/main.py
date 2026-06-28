from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .mesh_factory import export_glb

BASE_DIR = Path(__file__).resolve().parents[1]
STATIC_DIR = BASE_DIR / "static"
MODELS_DIR = STATIC_DIR / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Eye Geometry Backend", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class GeometryRequest(BaseModel):
    label: str = Field(default="Object")
    confidence: float = Field(default=0.7, ge=0, le=1)
    mode: str = Field(default="approximate")


class GeometryResponse(BaseModel):
    ok: bool
    engine: str
    status: str
    label: str
    model_name: str
    model_url: str
    download_url: str
    created_at: float
    notes: str


@app.get("/health")
def health():
    return {"ok": True, "service": "eye-geometry-backend", "time": time.time()}


@app.post("/v1/geometry/generate", response_model=GeometryResponse)
def generate_geometry(payload: GeometryRequest):
    """Generate a working GLB immediately using procedural geometry.

    This is the launchable Option A backend. The function boundary is intentionally
    stable so TripoSR, Stable Fast 3D, Shap-E, or a paid API can replace the
    internals without changing the Expo app.
    """
    label = payload.label or "Object"
    filename, _ = export_glb(label, MODELS_DIR)
    url = f"/static/models/{filename}"
    return GeometryResponse(
        ok=True,
        engine="eye-procedural-v1",
        status="done",
        label=label,
        model_name=filename,
        model_url=url,
        download_url=url,
        created_at=time.time(),
        notes="Generated procedural GLB draft from detected object label. Replace engine with Stable Fast 3D/TripoSR for photoreal mesh generation.",
    )


@app.post("/v1/geometry/generate-from-image", response_model=GeometryResponse)
async def generate_geometry_from_image(
    label: str = Form(default="Object"),
    confidence: float = Form(default=0.7),
    image: Optional[UploadFile] = File(default=None),
):
    # Image is accepted now to lock the production contract. Procedural v1 uses
    # the label; the next engine will use the image bytes for real reconstruction.
    if image is not None:
        await image.read()
    filename, _ = export_glb(label or "Object", MODELS_DIR)
    url = f"/static/models/{filename}"
    return GeometryResponse(
        ok=True,
        engine="eye-procedural-v1-image-contract",
        status="done",
        label=label or "Object",
        model_name=filename,
        model_url=url,
        download_url=url,
        created_at=time.time(),
        notes="Image upload contract is live. Procedural v1 used label fallback; real image-to-mesh engine plugs in here.",
    )


@app.get("/v1/geometry/models/{model_name}")
def download_model(model_name: str):
    path = MODELS_DIR / model_name
    return FileResponse(path, media_type="model/gltf-binary", filename=model_name)
