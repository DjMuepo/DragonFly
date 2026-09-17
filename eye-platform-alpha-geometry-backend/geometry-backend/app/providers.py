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
            from rembg import new_session
            from tsr.system import TSR
            from tsr.utils import remove_background, resize_foreground
        except ImportError as error:
            raise RuntimeError("TripoSR is not installed. Install requirements-ai.txt in a Python 3.11 environment.") from error

        device = "cuda" if torch.cuda.is_available() else "cpu"
        if device == "cpu" and os.environ.get("EYE_ALLOW_CPU_TRIPOSR") != "1":
            raise RuntimeError(
                "TripoSR requires a CUDA GPU for this deployment. CPU inference is experimental and disabled because it can exhaust "
                "the API worker; set EYE_ALLOW_CPU_TRIPOSR=1 only in a separately sized worker."
            )
        model = TSR.from_pretrained("stabilityai/TripoSR", config_name="config.yaml", weight_name="model.ckpt").to(device)
        model.renderer.set_chunk_size(8192 if device == "cuda" else 2048)
        image = resize_foreground(remove_background(Image.open(request.image_path).convert("RGB"), new_session()), 0.85)
        scene_codes = model(image, device=device)
        mesh = model.extract_mesh(scene_codes, has_vertex_color=False, resolution=256 if device == "cuda" else 128)[0]
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


class DPTDepthMeshProvider:
    name = "dpt-depth-mesh"

    def generate(self, request: ReconstructionRequest, models_dir: Path) -> ReconstructionOutput:
        if request.image_path is None or not request.image_path.exists():
            raise ValueError("DPT reconstruction requires an uploaded source image")
        try:
            import numpy as np
            import torch
            import torch.nn.functional as functional
            import trimesh
            from PIL import Image
            from transformers import DPTForDepthEstimation, DPTImageProcessor
        except ImportError as error:
            raise RuntimeError("DPT reconstruction dependencies are not installed") from error

        model_id = os.environ.get("EYE_DPT_MODEL", "Intel/dpt-hybrid-midas")
        image = Image.open(request.image_path).convert("RGB")
        processor = DPTImageProcessor.from_pretrained(model_id)
        model = DPTForDepthEstimation.from_pretrained(model_id).to("cpu").eval()
        inputs = processor(images=image, return_tensors="pt")
        with torch.no_grad():
            prediction = model(**inputs).predicted_depth
        depth = functional.interpolate(
            prediction.unsqueeze(1), size=(96, 96), mode="bicubic", align_corners=False
        ).squeeze().cpu().numpy()
        low, high = np.percentile(depth, [2, 98])
        normalized = np.clip((depth - low) / max(high - low, 1e-6), 0.0, 1.0)
        height, width = normalized.shape
        object_width = 80.0
        object_height = object_width * image.height / max(image.width, 1)
        relief_depth = 20.0
        backing_thickness = 2.0
        xs = np.linspace(-object_width / 2, object_width / 2, width)
        ys = np.linspace(object_height / 2, -object_height / 2, height)
        grid_x, grid_y = np.meshgrid(xs, ys)
        front = np.column_stack(
            (grid_x.ravel(), grid_y.ravel(), backing_thickness + normalized.ravel() * (relief_depth - backing_thickness))
        )
        back = front.copy()
        back[:, 2] = 0.0
        vertices = np.vstack((front, back))
        front_faces = []
        for row in range(height - 1):
            for column in range(width - 1):
                top_left = row * width + column
                top_right = top_left + 1
                bottom_left = top_left + width
                bottom_right = bottom_left + 1
                front_faces.extend(((top_left, bottom_left, top_right), (top_right, bottom_left, bottom_right)))
        face_count = len(front)
        back_faces = [(c + face_count, b + face_count, a + face_count) for a, b, c in front_faces]
        boundary = (
            list(range(width))
            + [row * width + width - 1 for row in range(1, height)]
            + list(range((height - 1) * width + width - 2, (height - 1) * width - 1, -1))
            + [row * width for row in range(height - 2, 0, -1)]
        )
        side_faces = []
        for index, current in enumerate(boundary):
            following = boundary[(index + 1) % len(boundary)]
            side_faces.extend(
                ((current, current + face_count, following), (following, current + face_count, following + face_count))
            )
        mesh = trimesh.Trimesh(vertices=vertices, faces=front_faces + back_faces + side_faces, process=True)
        model_name, model_path = export_trimesh(mesh, request.label, models_dir)
        return ReconstructionOutput(
            engine=self.name,
            model_name=model_name,
            model_path=model_path,
            stl_name=model_path.with_suffix(".stl").name,
            stl_path=model_path.with_suffix(".stl"),
            detected_family=infer_preset(request.label),
            notes=f"AI depth reconstruction completed on CPU with {model_id}.",
            provider_kind="ai",
        )


def select_provider() -> ReconstructionProvider:
    requested = os.environ.get("EYE_RECONSTRUCTION_PROVIDER", "dpt-depth-mesh").strip().lower()
    if requested in {"", "procedural", "parametric"}:
        return ProceduralProvider()
    if requested == "triposr":
        return TripoSRProvider()
    if requested in {"dpt", "dpt-depth-mesh"}:
        return DPTDepthMeshProvider()
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