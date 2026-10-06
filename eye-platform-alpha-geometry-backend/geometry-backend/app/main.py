from __future__ import annotations

import json
import time
import uuid
import os
from io import BytesIO
from pathlib import Path
from typing import Dict, Literal, Optional
from urllib.parse import urlparse

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from PIL import Image, UnidentifiedImageError

from .mesh_factory import infer_preset
from .mesh_factory import export_trimesh
from .mesh_editing import DeterministicMeshEditor, EditResult, FeatureEditingProvider, UnsupportedEditError, validate_for_print
from .image_preprocessing import prepare_reconstruction_image
from .physical_units import ScaleMetadata, calibrate_mesh, export_manufacturing_mesh, load_scale_metadata, mesh_from_glb_for_edit, save_scale_metadata
from .providers import ProceduralProvider, ReconstructionRequest, reconstruct, select_provider

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
    quality_mode: Literal["FAST", "STANDARD", "HIGH_QUALITY"] = "STANDARD"

class EditRequest(BaseModel):
    label: str = Field(default="Object")
    model_url: Optional[str] = None
    prompt: str = Field(default="make it printable")

class CalibrationRequest(BaseModel):
    label: str = Field(default="Object")
    model_url: str
    measurement: str

class GeometryResponse(BaseModel):
    ok: bool
    job_id: str
    engine: str
    provider_kind: str
    status: str
    label: str
    detected_family: str
    model_name: str
    model_url: str
    download_url: str
    stl_download_url: Optional[str] = None
    created_at: float
    notes: str
    change_kind: Optional[str] = None
    edit_summary: Optional[str] = None
    operations: list[str] = Field(default_factory=list)
    validation: Optional[dict] = None
    scale_status: str = "unknown"
    calibration: Optional[dict] = None
    quality_mode: str = "STANDARD"
    preprocessing: Optional[dict] = None
    hidden_surface_uncertainty: Optional[str] = None


class GeometryJobResponse(BaseModel):
    job_id: str
    status: str
    progress: int
    provider: str
    provider_kind: str
    quality_mode: str = "STANDARD"
    stage: Optional[str] = None
    stage_detail: Optional[str] = None
    preprocessing: Optional[dict] = None
    error: Optional[str] = None
    result: Optional[GeometryResponse] = None

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
    return (os.environ.get("PUBLIC_BASE_URL") or str(request.base_url)).rstrip("/")


def _model_response(base_url: str, job_id: str, label: str, generated, edit_metadata: Optional[dict] = None) -> GeometryResponse:
    model_path = f"/v1/geometry/models/{generated.model_name}"
    stl_path = f"/v1/geometry/models/{generated.stl_name}" if generated.stl_name else None
    model_url = f"{base_url}{model_path}"
    metadata = load_scale_metadata(generated.model_path)
    payload = GeometryResponse(
        ok=True,
        job_id=job_id,
        engine=generated.engine,
        provider_kind=generated.provider_kind,
        status="done",
        label=label or "Object",
        detected_family=generated.detected_family,
        model_name=generated.model_name,
        model_url=model_url,
        download_url=model_url,
        stl_download_url=f"{base_url}{stl_path}" if stl_path else None,
        created_at=time.time(),
        notes=generated.notes,
        scale_status=metadata.status,
        calibration={
            "axis": metadata.calibrated_axis,
            "value_mm": metadata.calibrated_value_mm,
            "source_measurement": metadata.source_measurement,
        } if metadata.status == "calibrated" else None,
        **(edit_metadata or {}),
    )
    return payload


def _run_generation(job_id: str, base_url: str, label: str, confidence: float, image_path: Path | None, prompt: str | None, quality_mode: str) -> None:
    job = JOBS[job_id]
    job.update(status="processing", progress=5, stage="validating", stage_detail="Checking photo dimensions and image quality.")
    prepared_path: Path | None = None
    try:
        preprocessing: dict | None = None
        if image_path is not None:
            job.update(progress=12, stage="segmenting", stage_detail="Removing the background and cropping the object.")
            prepared_path, prep_report = prepare_reconstruction_image(image_path, UPLOADS_DIR, quality_mode)
            preprocessing = prep_report.as_dict()
            job.update(progress=25, stage="preprocessed", stage_detail="Photo normalized; submitting reconstruction.", preprocessing=preprocessing)
        request = ReconstructionRequest(label=label, confidence=confidence, image_path=prepared_path, prompt=prompt, quality_mode=quality_mode)
        if image_path is None:
            generated = ProceduralProvider().generate(request, MODELS_DIR)
        else:
            job.update(progress=35, stage="reconstructing", stage_detail="Generating mesh with the selected AI provider.")
            generated = reconstruct(
                request,
                MODELS_DIR,
                allow_procedural_fallback=os.environ.get("EYE_ALLOW_PROCEDURAL_FALLBACK") == "1",
            )
        save_scale_metadata(generated.model_path, ScaleMetadata(status="unknown"))
        generated_mesh = __import__("trimesh").load(generated.model_path, force="mesh")
        generation_metadata = {
            "validation": validate_for_print(generated_mesh, "unknown"),
            "quality_mode": quality_mode,
            "preprocessing": preprocessing,
            "hidden_surface_uncertainty": "Single-photo geometry behind or occluded from the camera is inferred, not measured.",
        }
        job.update(
            status="done",
            progress=100,
            stage="complete",
            stage_detail="Model ready.",
            provider=generated.engine,
            provider_kind=generated.provider_kind,
            result=_model_response(base_url, job_id, label, generated, generation_metadata).model_dump(),
        )
    except Exception as error:
        job.update(status="error", progress=100, stage="error", stage_detail=str(error), error=str(error))
    finally:
        if prepared_path:
            prepared_path.unlink(missing_ok=True)


def _create_geometry_job(request: Request, background: BackgroundTasks, label: str, confidence: float, image_path: Path | None = None, prompt: str | None = None, quality_mode: str = "STANDARD") -> GeometryJobResponse:
    job_id = uuid.uuid4().hex[:12]
    provider = ProceduralProvider() if image_path is None else select_provider()
    provider_kind = "procedural_fallback" if provider.name == "procedural-parametric" else "ai"
    JOBS[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "progress": 0,
        "provider": provider.name,
        "provider_kind": provider_kind,
        "quality_mode": quality_mode,
        "stage": "queued",
        "stage_detail": "Waiting for reconstruction worker.",
        "preprocessing": None,
        "error": None,
        "result": None,
    }
    background.add_task(_run_generation, job_id, public_base(request), label, confidence, image_path, prompt, quality_mode)
    return GeometryJobResponse(**JOBS[job_id])


def _source_model_path(model_url: str | None) -> Path:
    if not model_url:
        raise UnsupportedEditError("Generate a model before editing it.")
    filename = Path(urlparse(model_url).path).name
    path = MODELS_DIR / filename
    if not filename.lower().endswith(".glb") or not path.is_file():
        raise UnsupportedEditError("The source model is unavailable. Return to the scan result and try again.")
    return path


def _run_edit(job_id: str, base_url: str, label: str, model_url: str | None, prompt: str) -> None:
    import trimesh
    from .providers import ReconstructionOutput

    job = JOBS[job_id]
    job.update(status="processing", progress=35)
    try:
        source_path = _source_model_path(model_url)
        scale_metadata = load_scale_metadata(source_path)
        feature_path = source_path.with_suffix(".features.json")
        try:
            feature_metadata = json.loads(feature_path.read_text(encoding="utf-8")) if feature_path.is_file() else {}
        except (OSError, json.JSONDecodeError):
            feature_metadata = {}
        source = mesh_from_glb_for_edit(source_path, scale_metadata)
        base_restore_mesh = None
        if "base" in prompt.lower() and any(word in prompt.lower().split() for word in ("remove", "delete")):
            restore_name = feature_metadata.get("editor_base_restore_model")
            if restore_name:
                restore_path = MODELS_DIR / Path(restore_name).name
                if not restore_path.is_file():
                    raise UnsupportedEditError("The original mesh revision for this fused base is unavailable; use Undo to restore it safely.")
                restore_metadata = load_scale_metadata(restore_path)
                base_restore_mesh = mesh_from_glb_for_edit(restore_path, restore_metadata)
        edited = DeterministicMeshEditor().apply(source, prompt, scale_status=scale_metadata.status, feature_metadata=feature_metadata, base_restore_mesh=base_restore_mesh)
        if scale_metadata.status == "calibrated":
            model_name, model_path = export_manufacturing_mesh(edited.mesh, f"{label}-edited", MODELS_DIR, scale_metadata, center=False)
        else:
            model_name, model_path = export_trimesh(edited.mesh, f"{label}-edited", MODELS_DIR, center=False)
            save_scale_metadata(model_path, scale_metadata)
        next_features = dict(feature_metadata) if edited.change_kind == "visual_only" else {}
        if edited.feature_metadata.get("remove_editor_base"):
            next_features.pop("editor_base_thickness_mm", None)
            next_features.pop("editor_base_overlap_mm", None)
            next_features.pop("editor_base_restore_model", None)
        else:
            next_features.update(edited.feature_metadata)
        if edited.feature_metadata.get("editor_base_thickness_mm"):
            next_features["editor_base_restore_model"] = source_path.name
        output_feature_path = model_path.with_suffix(".features.json")
        if next_features:
            output_feature_path.write_text(json.dumps(next_features, separators=(",", ":")), encoding="utf-8")
        else:
            output_feature_path.unlink(missing_ok=True)
        generated = ReconstructionOutput(
            engine="deterministic-mesh-editor",
            model_name=model_name,
            model_path=model_path,
            stl_name=model_path.with_suffix(".stl").name,
            stl_path=model_path.with_suffix(".stl"),
            detected_family=infer_preset(label),
            notes=edited.summary,
            provider_kind="deterministic_edit" if edited.change_kind == "geometry" else "visual_only",
        )
        metadata = {
            "change_kind": edited.change_kind,
            "edit_summary": edited.summary,
            "operations": edited.operations,
            "validation": validate_for_print(edited.mesh, scale_metadata.status),
        }
        job.update(
            status="done",
            progress=100,
            provider=generated.engine,
            provider_kind=generated.provider_kind,
            result=_model_response(base_url, job_id, label, generated, metadata).model_dump(),
        )
    except (UnsupportedEditError, ValueError) as error:
        job.update(status="error", progress=100, error=str(error))
    except Exception:
        job.update(status="error", progress=100, error="The model could not be edited. Try a simpler instruction.")


def _run_calibration(job_id: str, base_url: str, label: str, model_url: str, measurement: str) -> None:
    from .providers import ReconstructionOutput

    job = JOBS[job_id]
    job.update(status="processing", progress=35)
    try:
        calibrated_mesh, metadata = calibrate_mesh(_source_model_path(model_url), measurement)
        model_name, model_path = export_manufacturing_mesh(calibrated_mesh, f"{label}-calibrated", MODELS_DIR, metadata, center=False)
        generated = ReconstructionOutput(
            engine="physical-scale-calibrator",
            model_name=model_name,
            model_path=model_path,
            stl_name=model_path.with_suffix(".stl").name,
            stl_path=model_path.with_suffix(".stl"),
            detected_family=infer_preset(label),
            notes=f"Calibrated {metadata.calibrated_axis} to {metadata.calibrated_value_mm:g} mm.",
            provider_kind="calibration",
        )
        result_metadata = {
            "change_kind": "geometry",
            "edit_summary": generated.notes,
            "operations": ["uniform physical calibration"],
            "validation": validate_for_print(calibrated_mesh, "calibrated"),
        }
        job.update(status="done", progress=100, provider=generated.engine, provider_kind=generated.provider_kind, result=_model_response(base_url, job_id, label, generated, result_metadata).model_dump())
    except (UnsupportedEditError, ValueError) as error:
        job.update(status="error", progress=100, error=str(error))
    except Exception:
        job.update(status="error", progress=100, error="The model could not be calibrated. Check the measurement and try again.")


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

@app.post("/v1/geometry/generate", response_model=GeometryJobResponse, status_code=202)
def generate_geometry(payload: GeometryRequest, request: Request, background: BackgroundTasks):
    label = classify_label(payload.label)
    return _create_geometry_job(request, background, label, payload.confidence, prompt=payload.prompt, quality_mode=payload.quality_mode)

@app.post("/v1/geometry/generate-from-image", response_model=GeometryJobResponse, status_code=202)
async def generate_geometry_from_image(request: Request, background: BackgroundTasks, label: str = Form(default="Object"), confidence: float = Form(default=0.7), quality_mode: Literal["FAST", "STANDARD", "HIGH_QUALITY"] = Form(default="STANDARD"), image: Optional[UploadFile] = File(default=None)):
    if image is None:
        raise HTTPException(status_code=400, detail="An image is required for AI reconstruction")
    content = await image.read(15 * 1024 * 1024 + 1)
    if not content or len(content) > 15 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Upload a non-empty image smaller than 15 MB")
    try:
        with Image.open(BytesIO(content)) as source:
            source.verify()
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(status_code=400, detail="The uploaded file is not a valid image") from None
    saved_name = f"{uuid.uuid4().hex}_{Path(image.filename or 'scan.jpg').name}"
    image_path = UPLOADS_DIR / saved_name
    image_path.write_bytes(content)
    detected = classify_label(label, image_path.name if image_path else None)
    return _create_geometry_job(request, background, detected, confidence, image_path=image_path, quality_mode=quality_mode)

@app.post("/v1/geometry/edit", response_model=GeometryJobResponse, status_code=202)
def edit_geometry(payload: EditRequest, request: Request, background: BackgroundTasks):
    label = classify_label(payload.label)
    job_id = uuid.uuid4().hex[:12]
    JOBS[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "progress": 0,
        "provider": "deterministic-mesh-editor",
        "provider_kind": "deterministic_edit",
        "error": None,
        "result": None,
    }
    background.add_task(_run_edit, job_id, public_base(request), label, payload.model_url, payload.prompt)
    return GeometryJobResponse(**JOBS[job_id])


@app.post("/v1/geometry/calibrate", response_model=GeometryJobResponse, status_code=202)
def calibrate_geometry(payload: CalibrationRequest, request: Request, background: BackgroundTasks):
    label = classify_label(payload.label)
    job_id = uuid.uuid4().hex[:12]
    JOBS[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "progress": 0,
        "provider": "physical-scale-calibrator",
        "provider_kind": "calibration",
        "error": None,
        "result": None,
    }
    background.add_task(_run_calibration, job_id, public_base(request), label, payload.model_url, payload.measurement)
    return GeometryJobResponse(**JOBS[job_id])


@app.get("/v1/geometry/edit/capabilities")
def edit_capabilities():
    return {
        "deterministic": ["scale", "dimensions", "rotation", "position", "material color"],
        "features": list(FeatureEditingProvider.supported_features),
        "unsupported": ["fillets", "chamfers", "threads", "freeform additions", "semantic part removal"],
    }

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
    return GeometryJobResponse(**job)

@app.get("/v1/geometry/models/{model_name}")
def download_model(model_name: str):
    safe_name = Path(model_name).name
    path = MODELS_DIR / safe_name
    if not path.exists():
        raise HTTPException(status_code=404, detail="Model not found")
    media_type = "model/gltf-binary" if path.suffix.lower() == ".glb" else "model/stl"
    return FileResponse(path, media_type=media_type, filename=path.name)
