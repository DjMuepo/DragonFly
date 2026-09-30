from __future__ import annotations

import base64
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .mesh_factory import export_glb, export_trimesh, infer_preset


def _load_backend_env() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


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


class ReplicateGPUProvider:
    """Remote hosted-GPU single-image reconstruction via the Replicate API.

    Requires REPLICATE_API_TOKEN. Model defaults to a maintained Hunyuan3D-2
    version on Replicate; override with EYE_REPLICATE_MODEL_VERSION.
    """

    name = "replicate-remote-gpu"
    _API_BASE = "https://api.replicate.com/v1"

    def generate(self, request: ReconstructionRequest, models_dir: Path) -> ReconstructionOutput:
        _load_backend_env()
        if request.image_path is None or not request.image_path.exists():
            raise ValueError("Remote GPU reconstruction requires an uploaded source image")
        token = os.environ.get("REPLICATE_API_TOKEN")
        if not token:
            raise RuntimeError(
                "REPLICATE_API_TOKEN is not set. Create an account at https://replicate.com, "
                "generate an API token at https://replicate.com/account/api-tokens, and set "
                "REPLICATE_API_TOKEN in the backend environment."
            )
        model_ref = os.environ.get("EYE_REPLICATE_MODEL_VERSION", "").strip()
        if not model_ref:
            raise RuntimeError(
                "EYE_REPLICATE_MODEL_VERSION is not set. Pick a maintained image-to-3D model version id "
                "from https://replicate.com/explore (for example a Hunyuan3D-2, TRELLIS, or Stable Fast 3D "
                "model) and set EYE_REPLICATE_MODEL_VERSION."
            )

        image_data_url = self._encode_image(request.image_path)
        prediction_path, prediction_body, model_name = self._prediction_request(model_ref, image_data_url)
        prediction = self._request(
            "POST",
            prediction_path,
            token,
            prediction_body,
        )
        prediction_url = prediction["urls"]["get"]

        deadline = time.time() + 600
        while prediction.get("status") not in {"succeeded", "failed", "canceled"}:
            if time.time() > deadline:
                raise RuntimeError("Replicate prediction timed out after 10 minutes")
            time.sleep(3)
            prediction = self._request("GET", prediction_url, token, None, absolute=True)

        if prediction.get("status") != "succeeded":
            raise RuntimeError(f"Replicate prediction failed: {prediction.get('error') or prediction.get('status')}")

        mesh_url = self._find_mesh_url(prediction.get("output"))
        if not mesh_url:
            raise RuntimeError("Replicate prediction succeeded but returned no mesh output")

        import trimesh

        parsed_name = Path(urllib.parse.urlparse(mesh_url).path).name or "replicate-mesh.glb"
        local_path = models_dir / f"_remote_{parsed_name}"
        urllib.request.urlretrieve(mesh_url, local_path)
        mesh = trimesh.load(local_path, force="mesh")
        local_path.unlink(missing_ok=True)

        model_name, model_path = export_trimesh(mesh, request.label, models_dir)
        return ReconstructionOutput(
            engine=self.name,
            model_name=model_name,
            model_path=model_path,
            stl_name=model_path.with_suffix(".stl").name,
            stl_path=model_path.with_suffix(".stl"),
            detected_family=infer_preset(request.label),
            notes=f"Remote GPU reconstruction completed via Replicate ({model_name}).",
            provider_kind="ai",
        )

    @staticmethod
    def _prediction_request(model_ref: str, image_data_url: str) -> tuple[str, dict, str]:
        if ":" in model_ref and "/" in model_ref.split(":", 1)[0]:
            model_slug, _version = model_ref.split(":", 1)
            return "/predictions", {"version": _version, "input": {"image": image_data_url}}, model_slug
        return "/predictions", {"version": model_ref, "input": {"image": image_data_url}}, model_ref[:12]

    @staticmethod
    def _encode_image(image_path: Path) -> str:
        mime = mimetypes.guess_type(str(image_path))[0] or "image/jpeg"
        encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
        return f"data:{mime};base64,{encoded}"

    @staticmethod
    def _find_mesh_url(output) -> str | None:
        if isinstance(output, dict) and "mesh" in output:
            mesh = output["mesh"]
            if isinstance(mesh, str):
                return mesh
            found = ReplicateGPUProvider._find_mesh_url(mesh)
            if found:
                return found
        candidates: list[str] = []

        def collect(value):
            if isinstance(value, str):
                candidates.append(value)
            elif isinstance(value, dict):
                for item in value.values():
                    collect(item)
            elif isinstance(value, list):
                for item in value:
                    collect(item)

        collect(output)
        for url in candidates:
            path = urllib.parse.urlparse(url).path.lower()
            if path.endswith((".glb", ".obj", ".ply")):
                return url
        return candidates[0] if candidates else None

    @classmethod
    def _request(cls, method: str, path: str, token: str, body: dict | None, absolute: bool = False):
        import json

        url = path if absolute else f"{cls._API_BASE}{path}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as error:
            raw = error.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(raw)
                detail = payload.get("detail") or payload.get("title") or raw
            except json.JSONDecodeError:
                detail = raw or error.reason
            raise RuntimeError(f"Replicate API error {error.code}: {detail}") from error


def select_provider() -> ReconstructionProvider:
    _load_backend_env()
    requested = os.environ.get("EYE_RECONSTRUCTION_PROVIDER", "dpt-depth-mesh").strip().lower()
    if requested in {"", "procedural", "parametric"}:
        return ProceduralProvider()
    if requested == "triposr":
        return TripoSRProvider()
    if requested in {"dpt", "dpt-depth-mesh"}:
        return DPTDepthMeshProvider()
    if requested in {"replicate", "remote-gpu", "hunyuan3d", "trellis"}:
        return ReplicateGPUProvider()
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