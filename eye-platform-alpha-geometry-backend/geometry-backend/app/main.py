from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .mesh_factory import export_glb

BASE_DIR = Path(__file__).resolve().parents[1]
STATIC_DIR = BASE_DIR / "static"
MODELS_DIR = STATIC_DIR / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Eye Geometry Backend", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
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


def public_base(request: Request) -> str:
    return str(request.base_url).rstrip("/")


def make_response(request: Request, label: str, engine: str) -> GeometryResponse:
    filename, _ = export_glb(label or "Object", MODELS_DIR)
    model_path = f"/v1/geometry/models/{filename}"
    model_url = f"{public_base(request)}{model_path}"
    return GeometryResponse(
        ok=True,
        engine=engine,
        status="done",
        label=label or "Object",
        model_name=filename,
        model_url=model_url,
        download_url=model_url,
        created_at=time.time(),
        notes="Generated launch-safe procedural GLB. This endpoint is stable for replacing internals with Stable Fast 3D, TripoSR, Shap-E, or text-to-3D.",
    )


@app.get("/health")
def health():
    return {
        "ok": True,
        "service": "eye-geometry-backend",
        "time": time.time(),
        "models_dir": str(MODELS_DIR),
    }


@app.post("/v1/geometry/generate", response_model=GeometryResponse)
def generate_geometry(payload: GeometryRequest, request: Request):
    return make_response(request, payload.label, "eye-procedural-v1")


@app.post("/v1/geometry/generate-from-image", response_model=GeometryResponse)
async def generate_geometry_from_image(
    request: Request,
    label: str = Form(default="Object"),
    confidence: float = Form(default=0.7),
    image: Optional[UploadFile] = File(default=None),
):
    if image is not None:
        await image.read()
    return make_response(request, label or "Object", "eye-procedural-v1-image-contract")


@app.get("/v1/geometry/models/{model_name}")
def download_model(model_name: str):
    safe_name = Path(model_name).name
    path = MODELS_DIR / safe_name

    # Never throw a 500 because the viewer asks for an old hardcoded filename.
    # Generate a fallback GLB and serve it instead.
    if not path.exists():
        fallback_name, _ = export_glb("Object", MODELS_DIR)
        path = MODELS_DIR / fallback_name

    if not path.exists():
        raise HTTPException(status_code=404, detail="Model file not found")

    return FileResponse(path, media_type="model/gltf-binary", filename=path.name)
