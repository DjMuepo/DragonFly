from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .mesh_factory import export_glb, export_trimesh, infer_preset


@dataclass(frozen=True)
class ReconstructionRequest:
    label: str
    confidence: float
    image_path: Path | None = None
    prompt: str | None = None


@dataclass(frozen=True)
class ReconstructionOutput:
    engine: str
    model_name: str
    model_path: Path
    stl_name: str | None = None
    stl_path: Path | None = None
    detected_family: str = "object"
    notes: str = ""
    provider_kind: str = "procedural_fallback"


class ReconstructionProvider(Protocol):
    name: str

    def generate(self, request: ReconstructionRequest, models_dir: Path) -> ReconstructionOutput:
        ...


class ProceduralProvider:
    name = "procedural-parametric"

    def generate(self, request: ReconstructionRequest, models_dir: Path) -> ReconstructionOutput:
        model_name, model_path = export_glb(request.label, models_dir, prompt=request.prompt)
        return ReconstructionOutput(
            engine=self.name,
            model_name=model_name,
            model_path=model_path,
            stl_name=model_path.with_suffix(".stl").name,
            stl_path=model_path.with_suffix(".stl"),
            detected_family=infer_preset(request.label),
            notes="Validated procedural geometry generated as the guaranteed alpha fallback.",
            provider_kind="procedural_fallback",
        )


class UnavailableExternalProvider:
    """Reserved adapter point for Stable Fast 3D, TripoSR, TRELLIS, or Hunyuan3D."""

    def __init__(self, name: str):
        self.name = name

    def generate(self, request: ReconstructionRequest, models_dir: Path) -> ReconstructionOutput:
        raise RuntimeError(f"{self.name} is not configured")


class TripoSRProvider:
    name = "triposr"

    def generate(self, request: ReconstructionRequest, models_dir: Path) -> ReconstructionOutput:
        if request.image_path is None or not request.image_path.exists():
            raise ValueError("TripoSR requires an uploaded source image")
        try:
            source_dir = os.environ.get("EYE_TRIPOSR_SOURCE", "/opt/triposr")
            if source_dir not in sys.path:
                sys.path.insert(0, source_dir)
            import torch
            from PIL import Image
            from tsr.system import TSR
            from tsr.utils import remove_background, resize_foreground
        except ImportError as error:
            raise RuntimeError("TripoSR is not installed. Install requirements-ai.txt in a Python 3.11 environment.") from error

        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = TSR.from_pretrained("stabilityai/TripoSR", config_name="config.yaml", weight_name="model.ckpt")
        model.renderer.set_chunk_size(8192 if device == "cuda" else 2048)
        image = resize_foreground(remove_background(Image.open(request.image_path).convert("RGB")), 0.85)
        scene_codes = model(image, device=device)
        mesh = model.extract_mesh(scene_codes, resolution=256 if device == "cuda" else 128)[0]
        model_name, model_path = export_trimesh(mesh, request.label, models_dir)
        return ReconstructionOutput(
            engine=self.name,
            model_name=model_name,
            model_path=model_path,
            stl_name=model_path.with_suffix(".stl").name,
            stl_path=model_path.with_suffix(".stl"),
            detected_family=infer_preset(request.label),
            notes=f"TripoSR image reconstruction completed on {device}.",
            provider_kind="ai",
        )


def select_provider() -> ReconstructionProvider:
    requested = os.environ.get("EYE_RECONSTRUCTION_PROVIDER", "triposr").strip().lower()
    if requested in {"", "procedural", "parametric"}:
        return ProceduralProvider()
    if requested == "triposr":
        return TripoSRProvider()
    return UnavailableExternalProvider(requested)


def reconstruct(request: ReconstructionRequest, models_dir: Path, allow_procedural_fallback: bool = False) -> ReconstructionOutput:
    provider = select_provider()
    try:
        return provider.generate(request, models_dir)
    except Exception as error:
        if not allow_procedural_fallback:
            raise RuntimeError(f"{provider.name} reconstruction failed: {error}") from error
        fallback = ProceduralProvider().generate(request, models_dir)
        return ReconstructionOutput(
            **{**fallback.__dict__, "notes": f"{fallback.notes} Requested provider '{provider.name}' failed: {error}"}
        )