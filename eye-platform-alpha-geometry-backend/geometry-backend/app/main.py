from __future__ import annotations

import json
import logging
import time
import uuid
import os
import threading
from io import BytesIO
from pathlib import Path
from typing import Dict, Literal, Optional
from urllib.parse import urlparse

import hashlib

from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from PIL import Image, UnidentifiedImageError

from .mesh_factory import infer_preset
from .mesh_factory import export_trimesh
from .mesh_editing import DeterministicMeshEditor, EditResult, FeatureEditingProvider, UnsupportedEditError, validate_for_print
from .image_preprocessing import prepare_reconstruction_image
from .physical_units import ScaleMetadata, calibrate_mesh, export_manufacturing_mesh, load_scale_metadata, mesh_from_glb_for_edit, save_scale_metadata
from .providers import ProceduralProvider, ReconstructionRequest, reconstruct, select_provider
from .api_routes import build_router
from .cors import install_cors
from .request_limits import RequestSizeLimitMiddleware
from .projects import ProjectError
from .persistence.repository import QuotaExceeded
from .runtime import build_runtime

RUNTIME = build_runtime()
MODELS_DIR = RUNTIME.settings.models_dir
UPLOADS_DIR = RUNTIME.settings.uploads_dir
MODELS_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Eye Geometry Backend", version="0.4.0-alpha")
app.add_middleware(RequestSizeLimitMiddleware, upload_max_bytes=RUNTIME.settings.upload_max_bytes)
ALLOWED_ORIGINS = install_cors(app)
_router, _deps = build_router(RUNTIME)
app.include_router(_router)
optional_auth = _deps["optional_auth"]
public_base = _deps["public_base"]
JOBS = RUNTIME.jobs
PROJECTS = RUNTIME.projects


@app.exception_handler(HTTPException)
async def http_error_response(request: Request, error: HTTPException):
    if error.status_code in (401, 403):
        detail = error.detail if isinstance(error.detail, str) else "Request is not authorized."
        return JSONResponse(status_code=error.status_code, headers=error.headers, content={"ok": False, "error": detail, "detail": detail})
    return JSONResponse(status_code=error.status_code, headers=error.headers, content={"detail": error.detail})


@app.on_event("startup")
def recover_interrupted_jobs() -> None:
    RUNTIME.jobs.recover_interrupted()


@app.exception_handler(QuotaExceeded)
async def quota_exceeded_handler(request: Request, error: QuotaExceeded):
    return JSONResponse(status_code=429, content={"ok": False, "error": str(error), "error_code": error.code, "detail": str(error)})


LOGGER = logging.getLogger("uvicorn.error.dragonfly.reconstruction")
PREPROCESSING_LOCK = threading.Lock()


def _memory_rss_mib() -> float | None:
    try:
        for line in Path("/proc/self/status").read_text(encoding="ascii").splitlines():
            if line.startswith("VmRSS:"):
                return round(int(line.split()[1]) / 1024, 1)
    except (OSError, ValueError):
        pass
    return None


def _log_reconstruction_event(job_id: str, stage: str, **details) -> None:
    LOGGER.info(
        "reconstruction_event %s",
        json.dumps({"job_id": job_id, "stage": stage, "memory_rss_mib": _memory_rss_mib(), **details}, separators=(",", ":")),
    )

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
    project_id: Optional[str] = None

class CalibrationRequest(BaseModel):
    label: str = Field(default="Object")
    model_url: str
    measurement: str
    project_id: Optional[str] = None

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
    reconstruction_quality: Optional[dict] = None
    project_id: Optional[str] = None
    revision_id: Optional[str] = None
    revision_seq: Optional[int] = None


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
    error_code: Optional[str] = None
    result: Optional[GeometryResponse] = None
    project_id: Optional[str] = None
    replayed: bool = False

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
    photo_reconstruction = image_path is not None
    job.update(status="processing", progress=5, stage="validating", stage_detail="Checking photo dimensions and image quality.")
    prepared_path: Path | None = None
    active_stage = "validating"
    provider_name = job.get("provider", "procedural-parametric" if image_path is None else "replicate-remote-gpu")
    try:
        preprocessing: dict | None = None
        if image_path is not None:
            with Image.open(image_path) as uploaded:
                input_dimensions = uploaded.size
                input_format = uploaded.format
            active_stage = "preprocessing_wait"
            _log_reconstruction_event(job_id, active_stage, provider=provider_name, input_dimensions=input_dimensions, input_format=input_format, input_bytes=image_path.stat().st_size)
            job.update(progress=12, stage="preprocessing", stage_detail="Resizing and normalizing photo for the memory-limited reconstruction service.")
            active_stage = "preprocessing"
            with PREPROCESSING_LOCK:
                prepared_path, prep_report = prepare_reconstruction_image(image_path, UPLOADS_DIR, quality_mode, job_id)
            preprocessing = prep_report.as_dict()
            image_path.unlink(missing_ok=True)
            _log_reconstruction_event(job_id, "preprocessing_complete", provider=provider_name, input_dimensions=input_dimensions, processed_dimensions=prep_report.output_dimensions, segmenter=prep_report.foreground_segmenter, crop_applied=prep_report.object_crop_applied, processed_bytes=prepared_path.stat().st_size)
            job.update(progress=25, stage="preprocessed", stage_detail="Photo normalized; submitting reconstruction.", preprocessing=preprocessing)
        request = ReconstructionRequest(label=label, confidence=confidence, image_path=prepared_path, prompt=prompt, quality_mode=quality_mode, job_id=job_id, preprocessing=preprocessing)
        if image_path is None:
            generated = ProceduralProvider().generate(request, MODELS_DIR)
        else:
            if prepared_path is None or preprocessing is None:
                raise RuntimeError("Image preprocessing did not produce a provider input.")
            active_stage = "replicate_reconstruction"
            _log_reconstruction_event(job_id, "provider_request", provider=provider_name, processed_dimensions=preprocessing["output_dimensions"], provider_kind="ai")
            job.update(progress=35, stage="reconstructing", stage_detail="Generating mesh with the selected AI provider.")
            generated = reconstruct(
                request,
                MODELS_DIR,
                allow_procedural_fallback=os.environ.get("EYE_ALLOW_PROCEDURAL_FALLBACK") == "1",
            )
        active_stage = "result_validation"
        save_scale_metadata(generated.model_path, ScaleMetadata(status="unknown"))
        generation_metadata = {
            "quality_mode": quality_mode,
            "preprocessing": preprocessing,
            "hidden_surface_uncertainty": "Single-photo geometry behind or occluded from the camera is inferred, not measured.",
            "reconstruction_quality": generated.reconstruction_quality,
        }
        if generated.validation is not None:
            generation_metadata["validation"] = generated.validation
        elif not photo_reconstruction:
            generated_mesh = __import__("trimesh").load(generated.model_path, force="mesh")
            generation_metadata["validation"] = validate_for_print(generated_mesh, "unknown")
            del generated_mesh
        _log_reconstruction_event(job_id, "model_stored", provider=generated.engine, provider_kind=generated.provider_kind, model_name=generated.model_name, model_bytes=generated.model_path.stat().st_size, model_url=f"{base_url}/v1/geometry/models/{generated.model_name}", status="ok")
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
        _log_reconstruction_event(job_id, active_stage, provider=provider_name, status="error", error_type=type(error).__name__)
        uncertain = photo_reconstruction and active_stage in {"replicate_reconstruction", "result_validation"}
        job.update(
            status="error",
            progress=100,
            stage="error",
            stage_detail="The provider status is uncertain; a new attempt could create another paid prediction." if uncertain else "The reconstruction provider did not complete the job.",
            error="The provider status is uncertain. Check the saved project before starting another attempt." if uncertain else "Reconstruction failed. Try again later.",
            error_code="provider_outcome_unknown" if uncertain else "provider_failed",
        )
    finally:
        if prepared_path:
            prepared_path.unlink(missing_ok=True)
        if image_path:
            image_path.unlink(missing_ok=True)


def _present_job(job, base_url: str) -> GeometryJobResponse:
    data = dict(job)
    result = data.get("result")
    if data["status"] == "done" and result:
        name = Path(result.get("model_name", "")).name
        model_path = MODELS_DIR / name
        if not name or not model_path.is_file() or model_path.stat().st_size == 0:
            data.update(status="error", error="The model file is no longer available in storage.", error_code="artifact_missing", result=None)
        else:
            data["result"] = PROJECTS.sign_result(base_url, result)
    data["project_id"] = job.project_id
    return GeometryJobResponse(**data)


def _create_geometry_job(request: Request, background: BackgroundTasks, label: str, confidence: float, image_path: Path | None = None, prompt: str | None = None, quality_mode: str = "STANDARD", owner_id: str | None = None, source_file: str | None = None, idempotency_key: str | None = None, fingerprint: str | None = None) -> GeometryJobResponse:
    provider = ProceduralProvider() if image_path is None else select_provider()
    provider_kind = "procedural_fallback" if provider.name == "procedural-parametric" else "ai"
    extra = {"source_file": source_file, "fingerprint": fingerprint}
    try:
        job, created = JOBS.create("generate", owner_id, provider.name, provider_kind, quality_mode, extra=extra, idempotency_key=idempotency_key, stage_detail="Waiting for reconstruction worker.")
    except QuotaExceeded:
        if image_path:
            image_path.unlink(missing_ok=True)
        if source_file:
            RUNTIME.artifacts.delete_files([source_file])
        raise
    if not created:
        if fingerprint and job.extra.get("fingerprint") != fingerprint:
            raise HTTPException(status_code=409, detail="This Idempotency-Key was already used for a different request.")
        if image_path:
            image_path.unlink(missing_ok=True)
        if source_file:
            RUNTIME.artifacts.delete_files([source_file])
        response = _present_job(job, public_base(request))
        return response.model_copy(update={"replayed": True})
    background.add_task(_run_generation, job["job_id"], public_base(request), label, confidence, image_path, prompt, quality_mode)
    return _present_job(job, public_base(request))


def _queue_derived_job(request: Request, background: BackgroundTasks, kind: str, provider: str, provider_kind: str, user, model_url: str | None, project_id: str | None, idempotency_key: str | None, fingerprint: str, runner, *runner_args) -> GeometryJobResponse:
    filename = Path(urlparse(model_url or "").path).name
    try:
        project, revision = PROJECTS.authorize_model(user[0] if user else None, filename, project_id) if model_url else (None, None)
    except ProjectError as error:
        raise HTTPException(status_code=error.status_code, detail=str(error)) from None
    if revision:
        PROJECTS.restore_sidecars(revision)
    extra = {"fingerprint": fingerprint, "base_seq": revision["seq"] if revision else None}
    job, created = JOBS.create(kind, user[0]["id"] if project else None, provider, provider_kind, project_id=project["id"] if project else None, extra=extra, idempotency_key=idempotency_key)
    if not created:
        if job.extra.get("fingerprint") != fingerprint:
            raise HTTPException(status_code=409, detail="This Idempotency-Key was already used for a different request.")
        return _present_job(job, public_base(request)).model_copy(update={"replayed": True})
    background.add_task(runner, job["job_id"], public_base(request), *runner_args)
    return _present_job(job, public_base(request))


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
    return {"ok": True, "service": "eye-geometry-backend", "version": "0.4.0-alpha"}

@app.get("/health")
def health():
    database_integrity = RUNTIME.repo.integrity_check()
    directories_ready = all(path.is_dir() and os.access(path, os.W_OK | os.X_OK) for path in (RUNTIME.settings.data_dir, MODELS_DIR, UPLOADS_DIR, RUNTIME.settings.sources_dir))
    storage_ready = database_integrity == "ok" and directories_ready
    return {
        "ok": storage_ready,
        "service": "eye-geometry-backend",
        "version": "0.4.0-alpha",
        "time": time.time(),
        "storage": {
            "ready": storage_ready,
            "durable": RUNTIME.settings.durable,
            "database_integrity": database_integrity,
            "directories_ready": directories_ready,
            "migrations": "applied at startup",
            "external_backup_configured": RUNTIME.settings.backup_external_configured,
            "restore_tested_attested": RUNTIME.settings.backup_restore_tested,
            "warnings": RUNTIME.settings.warnings,
        },
    }

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
def generate_geometry(payload: GeometryRequest, request: Request, background: BackgroundTasks, idempotency_key: Optional[str] = Header(default=None), auth=Depends(optional_auth)):
    label = classify_label(payload.label)
    fingerprint = hashlib.sha256(json.dumps(payload.model_dump(), sort_keys=True).encode()).hexdigest()
    return _create_geometry_job(request, background, label, payload.confidence, prompt=payload.prompt, quality_mode=payload.quality_mode, owner_id=auth[0]["id"] if auth else None, idempotency_key=idempotency_key, fingerprint=fingerprint)

@app.post("/v1/geometry/generate-from-image", response_model=GeometryJobResponse, status_code=202)
async def generate_geometry_from_image(request: Request, background: BackgroundTasks, idempotency_key: Optional[str] = Header(default=None), auth=Depends(optional_auth), label: str = Form(default="Object"), confidence: float = Form(default=0.7), quality_mode: Literal["FAST", "STANDARD", "HIGH_QUALITY"] = Form(default="STANDARD"), image: Optional[UploadFile] = File(default=None)):
    if image is None:
        raise HTTPException(status_code=400, detail="An image is required for AI reconstruction")
    content = await image.read(RUNTIME.settings.upload_max_bytes + 1)
    if not content or len(content) > RUNTIME.settings.upload_max_bytes:
        raise HTTPException(status_code=413, detail="Upload exceeds the configured image size limit or is empty.")
    try:
        with Image.open(BytesIO(content)) as source:
            source.verify()
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(status_code=400, detail="The uploaded file is not a valid image") from None
    fingerprint = hashlib.sha256(content + f"|{label}|{confidence}|{quality_mode}".encode()).hexdigest()
    if idempotency_key:
        existing = JOBS.repo.find_job_by_idempotency(auth[0]["id"] if auth else "guest", idempotency_key)
        if existing:
            return _create_geometry_job(request, background, label, confidence, quality_mode=quality_mode, owner_id=auth[0]["id"] if auth else None, idempotency_key=idempotency_key, fingerprint=fingerprint)
    saved_name = f"{uuid.uuid4().hex}_{Path(image.filename or 'scan.jpg').name}"
    image_path = UPLOADS_DIR / saved_name
    image_path.write_bytes(content)
    source_file = RUNTIME.artifacts.save_source_image(content, image.filename or "scan.jpg").name if auth else None
    detected = classify_label(label, image_path.name if image_path else None)
    return _create_geometry_job(request, background, detected, confidence, image_path=image_path, quality_mode=quality_mode, owner_id=auth[0]["id"] if auth else None, source_file=source_file, idempotency_key=idempotency_key, fingerprint=fingerprint)

@app.post("/v1/geometry/edit", response_model=GeometryJobResponse, status_code=202)
def edit_geometry(payload: EditRequest, request: Request, background: BackgroundTasks, idempotency_key: Optional[str] = Header(default=None), auth=Depends(optional_auth)):
    label = classify_label(payload.label)
    fingerprint = hashlib.sha256(f"{payload.label}|{payload.model_url}|{payload.prompt}|{payload.project_id}".encode()).hexdigest()
    return _queue_derived_job(request, background, "edit", "deterministic-mesh-editor", "deterministic_edit", auth, payload.model_url, payload.project_id, idempotency_key, fingerprint, _run_edit, label, payload.model_url, payload.prompt)


@app.post("/v1/geometry/calibrate", response_model=GeometryJobResponse, status_code=202)
def calibrate_geometry(payload: CalibrationRequest, request: Request, background: BackgroundTasks, idempotency_key: Optional[str] = Header(default=None), auth=Depends(optional_auth)):
    label = classify_label(payload.label)
    fingerprint = hashlib.sha256(f"{payload.label}|{payload.model_url}|{payload.measurement}|{payload.project_id}".encode()).hexdigest()
    return _queue_derived_job(request, background, "calibrate", "physical-scale-calibrator", "calibration", auth, payload.model_url, payload.project_id, idempotency_key, fingerprint, _run_calibration, label, payload.model_url, payload.measurement)


@app.get("/v1/geometry/edit/capabilities")
def edit_capabilities():
    return {
        "deterministic": ["scale", "dimensions", "rotation", "position", "material color"],
        "features": list(FeatureEditingProvider.supported_features),
        "unsupported": ["fillets", "chamfers", "threads", "freeform additions", "semantic part removal"],
    }

@app.post("/v1/geometry/prepare-print")
def prepare_print(payload: PrintPrepRequest):
    raise HTTPException(
        status_code=501,
        detail="Slicer-based print preparation is not integrated. No printability check, material estimate or print time was produced.",
    )

@app.get("/v1/geometry/jobs/{job_id}")
def job_status(job_id: str, request: Request, auth=Depends(optional_auth)):
    job = JOBS.get(job_id)
    if not job or (job.owner_id and (auth is None or auth[0]["id"] != job.owner_id)):
        raise HTTPException(status_code=404, detail="Job not found")
    return _present_job(job, public_base(request))


@app.get("/v1/geometry/idempotency")
def idempotency_status(request: Request, idempotency_key: str = Header(alias="Idempotency-Key"), auth=Depends(optional_auth)):
    if len(idempotency_key) > 128 or any(char.isspace() for char in idempotency_key):
        raise HTTPException(status_code=400, detail="Invalid idempotency key.")
    scope = auth[0]["id"] if auth else "guest"
    row = RUNTIME.repo.find_job_by_idempotency(scope, idempotency_key)
    if not row:
        raise HTTPException(status_code=404, detail="No request was accepted for this idempotency key.")
    job = JOBS.get(row["id"])
    if not job:
        return {"job_id": row["id"], "status": row["status"], "replayed": True}
    return _present_job(job, public_base(request)).model_copy(update={"replayed": True})

@app.get("/v1/geometry/models/{model_name}")
def download_model(model_name: str, exp: Optional[str] = None, sig: Optional[str] = None, auth=Depends(optional_auth)):
    safe_name = Path(model_name).name
    artifact = RUNTIME.repo.get_artifact_by_filename(safe_name)
    if artifact and not (RUNTIME.artifacts.signature_valid(safe_name, exp, sig) or (auth and auth[0]["id"] == artifact["owner_id"])):
        raise HTTPException(status_code=404, detail="Model not found")
    path = MODELS_DIR / safe_name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Model file is not available in storage")
    media_type = "model/gltf-binary" if path.suffix.lower() == ".glb" else "model/stl"
    return FileResponse(path, media_type=media_type, filename=path.name)
