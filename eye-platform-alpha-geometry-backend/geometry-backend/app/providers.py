from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .mesh_factory import export_glb, infer_preset


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
        )


class UnavailableExternalProvider:
    """Reserved adapter point for Stable Fast 3D, TripoSR, TRELLIS, or Hunyuan3D."""

    def __init__(self, name: str):
        self.name = name

    def generate(self, request: ReconstructionRequest, models_dir: Path) -> ReconstructionOutput:
        raise RuntimeError(f"{self.name} is not configured")


def select_provider() -> ReconstructionProvider:
    requested = os.environ.get("EYE_RECONSTRUCTION_PROVIDER", "procedural").strip().lower()
    if requested in {"", "procedural", "parametric"}:
        return ProceduralProvider()
    return UnavailableExternalProvider(requested)


def reconstruct(request: ReconstructionRequest, models_dir: Path) -> ReconstructionOutput:
    provider = select_provider()
    try:
        return provider.generate(request, models_dir)
    except Exception as error:
        fallback = ProceduralProvider().generate(request, models_dir)
        return ReconstructionOutput(
            **{**fallback.__dict__, "notes": f"{fallback.notes} Requested provider '{provider.name}' failed: {error}"}
        )