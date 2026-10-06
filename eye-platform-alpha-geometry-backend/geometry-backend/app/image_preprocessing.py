from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal
from uuid import uuid4

import numpy as np
from PIL import Image, ImageOps, ImageStat, UnidentifiedImageError

QualityMode = Literal["FAST", "STANDARD", "HIGH_QUALITY"]
QUALITY_MAX_EDGE = {"FAST": 1024, "STANDARD": 2048, "HIGH_QUALITY": 4096}


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


def prepare_reconstruction_image(image_path: Path, uploads_dir: Path, quality_mode: str = "STANDARD") -> tuple[Path, ImagePreprocessingReport]:
    mode = quality_mode.strip().upper()
    if mode not in QUALITY_MAX_EDGE:
        raise ValueError("Choose FAST, STANDARD, or HIGH_QUALITY reconstruction quality.")
    try:
        with Image.open(image_path) as opened:
            opened.verify()
        with Image.open(image_path) as opened:
            image = ImageOps.exif_transpose(opened).convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise ValueError("The selected photo is invalid or too large to process safely.") from None

    source_dimensions = image.size
    if min(source_dimensions) < 128:
        raise ValueError("Use a sharper photo at least 128 pixels wide and tall.")
    if ImageStat.Stat(image.convert("L")).stddev[0] < 2.0:
        raise ValueError("The photo is nearly blank. Retake it with the object clearly visible.")

    try:
        from rembg import remove
    except ImportError as error:
        raise RuntimeError("Foreground segmentation is unavailable on this backend. Install the rembg CPU runtime before accepting reconstruction jobs.") from error

    model_name = "u2netp" if mode == "FAST" else "u2net"
    segmented = remove(image, session=_segmenter_session(model_name)).convert("RGBA")
    alpha = np.asarray(segmented.getchannel("A"))
    foreground = alpha > 12
    if not np.any(foreground):
        raise ValueError("No foreground object was found. Retake the photo with the object unobstructed.")
    rows, cols = np.nonzero(foreground)
    left, right = int(cols.min()), int(cols.max()) + 1
    top, bottom = int(rows.min()), int(rows.max()) + 1
    margin_x = max(2, int((right - left) * 0.05))
    margin_y = max(2, int((bottom - top) * 0.05))
    crop_box = (max(0, left - margin_x), max(0, top - margin_y), min(segmented.width, right + margin_x), min(segmented.height, bottom + margin_y))
    segmented = segmented.crop(crop_box)

    max_edge = QUALITY_MAX_EDGE[mode]
    longest = max(segmented.size)
    resized = longest > max_edge
    if resized:
        factor = max_edge / longest
        target = (max(1, round(segmented.width * factor)), max(1, round(segmented.height * factor)))
        segmented = segmented.resize(target, Image.Resampling.LANCZOS)

    uploads_dir.mkdir(parents=True, exist_ok=True)
    output_path = uploads_dir / f"prepared_{uuid4().hex}.png"
    segmented.save(output_path, format="PNG", optimize=True)
    report = ImagePreprocessingReport(mode, source_dimensions, segmented.size, model_name, True, resized)
    return output_path, report
