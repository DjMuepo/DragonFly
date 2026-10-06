from __future__ import annotations

import logging
import json
import os
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal
from uuid import uuid4

import numpy as np
from PIL import Image, ImageOps, ImageStat, UnidentifiedImageError

QualityMode = Literal["FAST", "STANDARD", "HIGH_QUALITY"]
QUALITY_MAX_EDGE = {"FAST": 1024, "STANDARD": 1280, "HIGH_QUALITY": 1536}
LOGGER = logging.getLogger("dragonfly.image_preprocessing")


@lru_cache(maxsize=2)
def _segmenter_session(model_name: str):
    from rembg import new_session

    return new_session(model_name)


@dataclass(frozen=True)
class ImagePreprocessingReport:
    quality_mode: QualityMode
    source_dimensions: tuple[int, int]
    output_dimensions: tuple[int, int]
    foreground_segmenter: str
    object_crop_applied: bool
    resized: bool
    source_images: int = 1
    hidden_surfaces: str = "inferred_from_single_view_not_measured"

    def as_dict(self) -> dict:
        value = asdict(self)
        value["source_dimensions"] = list(self.source_dimensions)
        value["output_dimensions"] = list(self.output_dimensions)
        return value


def prepare_reconstruction_image(image_path: Path, uploads_dir: Path, quality_mode: str = "STANDARD", job_id: str | None = None) -> tuple[Path, ImagePreprocessingReport]:
    mode = quality_mode.strip().upper()
    if mode not in QUALITY_MAX_EDGE:
        raise ValueError("Choose FAST, STANDARD, or HIGH_QUALITY reconstruction quality.")
    try:
        with Image.open(image_path) as opened:
            opened.verify()
        with Image.open(image_path) as opened:
            source_dimensions = opened.size
            image_format = opened.format
            orientation = opened.getexif().get(274, 1)
            max_edge = QUALITY_MAX_EDGE[mode]
            if image_format == "JPEG":
                opened.draft("RGB", (max_edge, max_edge))
            oriented = ImageOps.exif_transpose(opened)
            oriented.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
            image = oriented.convert("RGB")
            if oriented is not opened:
                oriented.close()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise ValueError("The selected photo is invalid or too large to process safely.") from None

    LOGGER.info(
        "reconstruction_event %s",
        json.dumps({
            "job_id": job_id,
            "stage": "preprocessing_decode_complete",
            "input_dimensions": source_dimensions,
            "decoded_dimensions": image.size,
            "image_format": image_format,
            "exif_orientation": orientation,
        }, separators=(",", ":")),
    )
    if min(source_dimensions) < 128:
        image.close()
        raise ValueError("Use a sharper photo at least 128 pixels wide and tall.")
    grayscale = image.convert("L")
    image_stddev = ImageStat.Stat(grayscale).stddev[0]
    grayscale.close()
    if image_stddev < 2.0:
        image.close()
        raise ValueError("The photo is nearly blank. Retake it with the object clearly visible.")

    uploads_dir.mkdir(parents=True, exist_ok=True)
    max_edge = QUALITY_MAX_EDGE[mode]
    if os.environ.get("EYE_LOCAL_SEGMENTATION", "0").strip() == "1":
        try:
            from rembg import remove
        except ImportError as error:
            image.close()
            raise RuntimeError("Local foreground segmentation is enabled but rembg is unavailable.") from error
        model_name = "u2netp" if mode == "FAST" else "u2net"
        segmented = remove(image, session=_segmenter_session(model_name)).convert("RGBA")
        image.close()
        alpha = np.asarray(segmented.getchannel("A"))
        foreground = alpha > 12
        if not np.any(foreground):
            segmented.close()
            raise ValueError("No foreground object was found. Retake the photo with the object unobstructed.")
        rows, cols = np.nonzero(foreground)
        left, right = int(cols.min()), int(cols.max()) + 1
        top, bottom = int(rows.min()), int(rows.max()) + 1
        margin_x = max(2, int((right - left) * 0.05))
        margin_y = max(2, int((bottom - top) * 0.05))
        crop_box = (max(0, left - margin_x), max(0, top - margin_y), min(segmented.width, right + margin_x), min(segmented.height, bottom + margin_y))
        cropped = segmented.crop(crop_box)
        segmented.close()
        output_path = uploads_dir / f"prepared_{uuid4().hex}.png"
        cropped.save(output_path, format="PNG", optimize=True)
        report = ImagePreprocessingReport(mode, source_dimensions, cropped.size, model_name, True, False)
        cropped.close()
    else:
        output_path = uploads_dir / f"prepared_{uuid4().hex}.jpg"
        image.save(output_path, format="JPEG", quality=88, optimize=False)
        report = ImagePreprocessingReport(mode, source_dimensions, image.size, "bypassed_resource_safe", False, image.size != source_dimensions)
        image.close()

    LOGGER.info(
        "reconstruction_event %s",
        json.dumps({
            "job_id": job_id,
            "stage": "preprocessing_complete",
            "processed_dimensions": report.output_dimensions,
            "segmenter": report.foreground_segmenter,
            "crop_applied": report.object_crop_applied,
            "processed_bytes": output_path.stat().st_size,
            "status": "ok",
        }, separators=(",", ":")),
    )
    return output_path, report
