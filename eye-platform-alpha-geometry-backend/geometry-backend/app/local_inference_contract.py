from __future__ import annotations

import hashlib
import math
import struct
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Protocol


class InferenceState(str, Enum):
    QUEUED = "queued"
    LOADING_MODEL = "loading_model"
    RUNNING = "running"
    EXPORTING = "exporting"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class ModelIdentity:
    model_id: str
    revision: str
    weights_sha256: str
    weight_license_source: str
    commercial_use_reviewed: bool = False

    def __post_init__(self) -> None:
        if not self.model_id.strip() or not self.revision.strip() or not self.weight_license_source.strip():
            raise ValueError("Model, exact revision and weight-license source are required.")
        _validate_sha256(self.weights_sha256)


def _validate_sha256(value: str) -> None:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ValueError("Expected a lowercase SHA-256 checksum.")


def _file_sha256(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


@dataclass(frozen=True)
class ResourceSample:
    host_rss_mib: float | None = None
    gpu_used_mib: float | None = None
    gpu_total_mib: float | None = None
    elapsed_seconds: float | None = None
    device: str | None = None

    def __post_init__(self) -> None:
        for value in (self.host_rss_mib, self.gpu_used_mib, self.gpu_total_mib, self.elapsed_seconds):
            if value is not None and (not math.isfinite(value) or value < 0):
                raise ValueError("Measured resources must be finite and nonnegative; use None when unknown.")


@dataclass(frozen=True)
class LocalInferenceRequest:
    request_id: str
    image_path: Path
    image_sha256: str
    model: ModelIdentity
    parameters: dict = field(default_factory=dict)
    max_image_bytes: int = 15 * 1024 * 1024
    max_image_pixels: int = 40_000_000

    def validate_input(self) -> dict:
        from PIL import Image

        if not self.request_id.strip() or self.max_image_bytes <= 0 or self.max_image_pixels <= 0:
            raise ValueError("A request identity and positive input limits are required.")
        _validate_sha256(self.image_sha256)
        if not self.model.commercial_use_reviewed:
            raise PermissionError("Model-weight commercial-use review is required before owner-controlled inference.")
        if not self.image_path.is_file() or not 0 < self.image_path.stat().st_size <= self.max_image_bytes:
            raise ValueError("Input image is missing, empty or over the configured byte limit.")
        if _file_sha256(self.image_path) != self.image_sha256:
            raise ValueError("Input image checksum mismatch.")
        with Image.open(self.image_path) as image:
            image.verify()
        with Image.open(self.image_path) as image:
            if image.format not in {"JPEG", "PNG", "WEBP"}:
                raise ValueError("Unsupported image format; no implicit conversion is performed by this contract.")
            if image.width * image.height > self.max_image_pixels:
                raise ValueError("Input exceeds the configured decoded-pixel limit.")
            metadata = {"format": image.format, "dimensions": list(image.size), "mode": image.mode, "exif_orientation": image.getexif().get(274, 1)}
        return metadata


@dataclass(frozen=True)
class InferenceError:
    code: str
    message: str
    retryable: bool = False

    def __post_init__(self) -> None:
        if not self.code.strip() or not self.message.strip():
            raise ValueError("Errors require a stable code and a safe user-visible message.")


@dataclass(frozen=True)
class GLBArtifact:
    path: Path
    sha256: str
    generated_by: ModelIdentity
    input_sha256: str
    execution_id: str

    def validate_container(self, max_bytes: int = 100 * 1024 * 1024) -> None:
        _validate_sha256(self.sha256)
        _validate_sha256(self.input_sha256)
        if not self.execution_id.strip() or max_bytes <= 0:
            raise ValueError("A model execution receipt and positive output limit are required.")
        size = self.path.stat().st_size
        if not 20 <= size <= max_bytes:
            raise ValueError("GLB container size is outside configured bounds.")
        with self.path.open("rb") as stream:
            magic, version, declared_size = struct.unpack("<4sII", stream.read(12))
        if magic != b"glTF" or version != 2 or declared_size != size:
            raise ValueError("Invalid GLB v2 container header.")
        if _file_sha256(self.path) != self.sha256:
            raise ValueError("GLB checksum mismatch.")


@dataclass(frozen=True)
class InferenceStatus:
    job_id: str
    state: InferenceState
    progress: float
    resources: ResourceSample = field(default_factory=ResourceSample)
    error: InferenceError | None = None
    artifact: GLBArtifact | None = None

    def __post_init__(self) -> None:
        if not self.job_id.strip() or not isinstance(self.state, InferenceState) or not math.isfinite(self.progress) or not 0 <= self.progress <= 100:
            raise ValueError("Status requires a job identity, typed state and progress between zero and 100.")
        if self.state == InferenceState.COMPLETE:
            if self.artifact is None or self.error is not None or self.progress != 100:
                raise ValueError("Completion requires an artifact, no error, and progress 100; never a procedural substitute.")
            self.artifact.validate_container()
        elif self.artifact is not None:
            raise ValueError("An artifact cannot be published before successful completion.")
        if self.state == InferenceState.FAILED and self.error is None:
            raise ValueError("Failed inference requires a structured error.")
        if self.error is not None and self.state not in {InferenceState.FAILED, InferenceState.CANCELLED}:
            raise ValueError("Errors cannot be combined with a successful or running status.")


class LocalGPUInferenceAdapter(Protocol):
    name: str

    def submit(self, request: LocalInferenceRequest) -> str: ...

    def status(self, job_id: str) -> InferenceStatus: ...

    def cancel(self, job_id: str) -> None: ...

    def resources(self) -> ResourceSample: ...