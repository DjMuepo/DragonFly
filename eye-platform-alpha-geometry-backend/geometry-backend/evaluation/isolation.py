from __future__ import annotations

import hashlib
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np
from PIL import Image

from app.image_preprocessing import prepare_reconstruction_image


def digest(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


@dataclass
class PreparedInput:
    path: Path
    metadata: dict
    mask: Path | None = None
    preview: Path | None = None


class SegmentationProvider(Protocol):
    name: str

    def prepare(self, baseline: PreparedInput, directory: Path) -> PreparedInput: ...


def prepare_baseline(source: Path, directory: Path, quality: str = "STANDARD") -> PreparedInput:
    if os.environ.get("EYE_LOCAL_SEGMENTATION", "0") != "0":
        raise ValueError("Evaluation baseline requires the deployed memory-safe EYE_LOCAL_SEGMENTATION=0 profile.")
    directory.mkdir(parents=True, exist_ok=True)
    path, report = prepare_reconstruction_image(source, directory, quality)
    destination = directory / "baseline.jpg"
    path.replace(destination)
    return PreparedInput(destination, {"provider": "production_baseline", "source_sha256": digest(source), **report.as_dict()})


class BaselineSegmentation:
    name = "baseline"

    def prepare(self, baseline: PreparedInput, directory: Path) -> PreparedInput:
        directory.mkdir(parents=True, exist_ok=True)
        destination = directory / "input.jpg"
        shutil.copyfile(baseline.path, destination)
        return PreparedInput(destination, {"provider": self.name, "fallback": True, "image_sha256": digest(destination)})


class GrabCutSegmentation:
    name = "grabcut_experimental_v1"

    def prepare(self, baseline: PreparedInput, directory: Path) -> PreparedInput:
        if os.environ.get("DRAGONFLY_EVAL_GRABCUT", "0") != "1":
            raise PermissionError("Experimental isolation is disabled; set DRAGONFLY_EVAL_GRABCUT=1 for local evaluation only.")
        import cv2

        cv2.setNumThreads(1)
        cv2.setRNGSeed(0)
        directory.mkdir(parents=True, exist_ok=True)
        with Image.open(baseline.path) as opened:
            full = np.asarray(opened.convert("RGB"))
        scale = min(1.0, 512 / max(full.shape[:2]))
        work = cv2.resize(full, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(work, cv2.COLOR_RGB2GRAY)
        height, width = gray.shape
        labels = np.full(gray.shape, cv2.GC_PR_BGD, np.uint8)
        border = max(2, int(min(gray.shape) * 0.03))
        labels[:border] = labels[-border:] = cv2.GC_BGD
        labels[:, :border] = labels[:, -border:] = cv2.GC_BGD
        edges = cv2.Canny(gray, 35, 110)
        density = cv2.GaussianBlur(edges.astype(np.float32), (0, 0), max(1, width * 0.06))
        density /= max(float(density.max()), 1)
        rows, columns = np.mgrid[:height, :width]
        centre = np.exp(-(((columns - width / 2) / (0.4 * width)) ** 2 + ((rows - height / 2) / (0.4 * height)) ** 2))
        prior = density * centre
        labels[(prior > 0.3) & (labels != cv2.GC_BGD)] = cv2.GC_PR_FGD
        labels[(prior > 0.6) & (labels != cv2.GC_BGD)] = cv2.GC_FGD
        warnings = ["Confidence is an uncalibrated heuristic, not proof of isolation accuracy."]
        failure = None
        try:
            cv2.grabCut(cv2.cvtColor(work, cv2.COLOR_RGB2BGR), labels, None, np.zeros((1, 65)), np.zeros((1, 65)), 5, cv2.GC_INIT_WITH_MASK)
            mask = np.isin(labels, (cv2.GC_FGD, cv2.GC_PR_FGD))
        except cv2.error:
            mask = np.zeros(gray.shape, bool)
            failure = "GrabCut could not identify foreground; baseline retained."
        count, components, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8))
        areas = sorted((int(value) for value in stats[1:, cv2.CC_STAT_AREA]), reverse=True)
        large_count = sum(area >= max(8, sum(areas) * 0.1) for area in areas)
        coverage = float(mask.mean())
        nearby = cv2.dilate(mask.astype(np.uint8), np.ones((25, 25), np.uint8)).astype(bool)
        edge_pixels = edges > 0
        omitted = float((edge_pixels & nearby & ~mask).sum() / max(int((edge_pixels & nearby).sum()), 1))
        boundary = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
        gradient = cv2.magnitude(cv2.Sobel(gray, cv2.CV_32F, 1, 0), cv2.Sobel(gray, cv2.CV_32F, 0, 1))
        alignment = float((gradient[boundary] > np.percentile(gradient, 65)).mean()) if boundary.any() else 0.0
        foreground, background = gray[mask], gray[~mask]
        contrast = min(1.0, abs(float(foreground.mean()) - float(background.mean())) / (float(background.std()) + 16) / 1.8) if foreground.size and background.size else 0.0
        plausible_coverage = float(np.clip(1 - abs(coverage - 0.24) / 0.42, 0, 1))
        confidence = float(np.clip(0.3 * alignment + 0.3 * contrast + 0.2 * plausible_coverage + 0.2 - 0.65 * omitted, 0, 1))
        ambiguous = large_count > 1 or coverage < 0.02 or coverage > 0.85 or omitted > 0.22
        if large_count > 1:
            warnings.append("Multiple possible foreground objects; no components were silently discarded.")
        if contrast < 0.6 or omitted > 0.15:
            warnings.append("Transparent, reflective, low-contrast or thin features may be missing; check handles and edges.")
        if background.size and float((background < 0.35 * np.median(gray)).mean()) > 0.2:
            warnings.append("Strong dark regions or shadows; diffuse lighting is recommended.")
        warnings.append("Reflections and clutter cannot be reliably distinguished from object geometry; use a matte uncluttered surface when uncertain.")
        if failure:
            warnings.append(failure)
        fallback = failure is not None or ambiguous or confidence < 0.70
        full_mask = cv2.resize(mask.astype(np.uint8) * 255, (full.shape[1], full.shape[0]), interpolation=cv2.INTER_NEAREST)
        mask_path = directory / "mask.png"
        Image.fromarray(full_mask).save(mask_path)
        soft = cv2.GaussianBlur(cv2.dilate(full_mask, np.ones((3, 3), np.uint8)), (0, 0), 1).astype(np.float32) / 255
        isolated = (full.astype(np.float32) * soft[..., None] + 255 * (1 - soft[..., None])).clip(0, 255).astype(np.uint8)
        preview = directory / "isolated-preview.jpg"
        Image.fromarray(isolated).save(preview, quality=88)
        destination = directory / "input.jpg"
        if fallback:
            shutil.copyfile(baseline.path, destination)
            warnings.append("Uncertain isolation: exact production baseline bytes selected.")
        else:
            shutil.copyfile(preview, destination)
        return PreparedInput(destination, {
            "provider": self.name, "fallback": fallback, "confidence": round(confidence, 4),
            "confidence_calibrated": False, "threshold": 0.70, "coverage": coverage,
            "edge_alignment": alignment, "nearby_edges_omitted": omitted,
            "foreground_background_contrast": contrast, "surface_regions": count - 1,
            "large_regions": large_count, "components_discarded": 0,
            "warnings": warnings, "image_sha256": digest(destination),
        }, mask_path, preview)


SEGMENTATION_PROVIDERS: dict[str, type[SegmentationProvider]] = {
    "baseline": BaselineSegmentation,
    "grabcut": GrabCutSegmentation,
}