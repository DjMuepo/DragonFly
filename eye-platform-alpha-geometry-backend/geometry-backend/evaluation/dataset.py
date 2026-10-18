from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

from .isolation import digest


CATEGORIES = ("opaque", "transparent", "reflective", "geometric", "irregular")
FIXTURES = (
    ("bottle", "opaque", "plain"),
    ("ceramic-mug", "opaque", "thin-handle"),
    ("clear-cup", "transparent", "reflection"),
    ("transparent-container", "transparent", "low-contrast"),
    ("metal-utensil", "reflective", "thin-structure"),
    ("glossy-object", "reflective", "shadow"),
    ("cardboard-box", "geometric", "plain"),
    ("mechanical-component", "geometric", "opening"),
    ("shoe", "irregular", "clutter"),
    ("toy", "irregular", "multiple-foreground"),
    ("complex-household-object", "irregular", "complex-silhouette"),
)


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_identifier(identifier: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", identifier):
        raise ValueError("Case IDs must contain 1-64 letters, numbers, underscores or hyphens.")


def load_dataset(root: Path) -> list[dict]:
    data = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    if data.get("version") != 1:
        raise ValueError("Unsupported dataset manifest version.")
    identifiers = set()
    for case in data["cases"]:
        validate_identifier(case["id"])
        if case["id"] in identifiers or case["category"] not in CATEGORIES:
            raise ValueError("Duplicate case ID or unknown category.")
        identifiers.add(case["id"])
        if case["kind"] not in {"synthetic", "photo", "screenshot_proxy"}:
            raise ValueError("Case kind must distinguish real photos from synthetic fixtures and screenshots.")
        for field in ("image", "expected_mask", "important_details_mask"):
            if case.get(field):
                path = (root / case[field]).resolve()
                if not path.is_relative_to(root.resolve()) or not path.is_file():
                    raise ValueError(f"Missing or out-of-dataset {field} for {case['id']}.")
        if digest(root / case["image"]) != case["sha256"]:
            raise ValueError(f"Original image checksum changed: {case['id']}.")
    return data["cases"]


def add_case(root: Path, source: Path, identifier: str, category: str, object_name: str, kind: str, lighting: str, background: str, conditions: list[str], silhouette: str, dimensions: dict | None = None, mask: Path | None = None, details: Path | None = None, attribution: str | None = None) -> dict:
    validate_identifier(identifier)
    if category not in CATEGORIES or kind not in {"synthetic", "photo", "screenshot_proxy"}:
        raise ValueError("Invalid category or evidence kind.")
    if dimensions and any(not isinstance(value, (int, float)) or value <= 0 for value in dimensions.values()):
        raise ValueError("Known dimensions must be positive millimeter values.")
    root.mkdir(parents=True, exist_ok=True)
    manifest = root / "manifest.json"
    cases = load_dataset(root) if manifest.exists() else []
    if any(case["id"] == identifier for case in cases):
        raise ValueError(f"Case already exists: {identifier}.")
    case_dir = root / identifier
    case_dir.mkdir()
    destination = case_dir / f"original{source.suffix.lower()}"
    shutil.copyfile(source, destination)
    with Image.open(destination) as image:
        metadata = {"pixel_dimensions": list(image.size), "format": image.format, "mode": image.mode, "exif_orientation": image.getexif().get(274, 1)}
    expected_size = tuple(reversed(metadata["pixel_dimensions"])) if metadata["exif_orientation"] in (5, 6, 7, 8) else tuple(metadata["pixel_dimensions"])
    for provided in (mask, details):
        if provided:
            with Image.open(provided) as annotation:
                if annotation.size != expected_size:
                    raise ValueError("Annotations must match full-resolution EXIF-oriented source dimensions.")
                if not annotation.convert("L").getbbox():
                    raise ValueError("Annotation contains no foreground.")
    case = {
        "id": identifier, "category": category, "object": object_name, "kind": kind,
        "image": str(destination.relative_to(root)), "sha256": digest(destination),
        "lighting": lighting, "background": background, "conditions": conditions,
        "known_dimensions_mm": dimensions, "expected_silhouette": silhouette,
        "added_at": timestamp(), "attribution": attribution, **metadata,
    }
    for field, provided in (("expected_mask", mask), ("important_details_mask", details)):
        if provided:
            target = case_dir / f"{field}.png"
            shutil.copyfile(provided, target)
            case[field] = str(target.relative_to(root))
        else:
            case[field] = None
    cases.append(case)
    manifest.write_text(json.dumps({"version": 1, "cases": cases}, indent=2), encoding="utf-8")
    return case


def initialize_fixtures(root: Path) -> list[dict]:
    if (root / "manifest.json").exists():
        raise ValueError("Dataset already exists; use add rather than overwriting originals.")
    root.mkdir(parents=True, exist_ok=True)
    scratch = root / "_fixture_source"
    scratch.mkdir()
    for object_name, category, condition in FIXTURES:
        mask = Image.new("L", (512, 512), 0)
        details = Image.new("L", mask.size, 0)
        drawing, detail_drawing = ImageDraw.Draw(mask), ImageDraw.Draw(details)
        if object_name == "bottle":
            drawing.rounded_rectangle((175, 160, 320, 420), 24, fill=255)
            drawing.rectangle((215, 90, 280, 170), fill=255)
        elif object_name == "ceramic-mug":
            drawing.ellipse((280, 190, 395, 340), fill=255)
            drawing.ellipse((310, 215, 370, 315), fill=0)
            detail_drawing.ellipse((280, 190, 395, 340), fill=255)
            detail_drawing.ellipse((310, 215, 370, 315), fill=0)
            drawing.rounded_rectangle((130, 150, 315, 380), 16, fill=255)
        elif object_name == "clear-cup":
            drawing.polygon(((155, 100), (355, 100), (315, 305), (195, 305)), fill=255)
        elif object_name == "transparent-container":
            drawing.rounded_rectangle((140, 140, 370, 375), 20, fill=255)
        elif object_name == "metal-utensil":
            drawing.ellipse((220, 95, 290, 205), fill=255)
            drawing.rectangle((248, 180, 261, 430), fill=255)
            detail_drawing.rectangle((248, 180, 261, 430), fill=255)
        elif object_name in {"glossy-object", "toy"}:
            drawing.ellipse((145, 130, 360, 380), fill=255)
        elif object_name == "mechanical-component":
            drawing.rectangle((130, 170, 365, 350), fill=255)
            drawing.ellipse((205, 200, 295, 290), fill=0)
            detail_drawing.ellipse((195, 190, 305, 300), fill=255)
            detail_drawing.ellipse((205, 200, 295, 290), fill=0)
        elif object_name == "shoe":
            drawing.polygon(((100, 320), (175, 185), (240, 250), (390, 310), (400, 365), (100, 365)), fill=255)
        elif object_name == "complex-household-object":
            drawing.polygon(((140, 370), (170, 130), (220, 210), (280, 100), (320, 240), (390, 180), (360, 390)), fill=255)
        else:
            drawing.rectangle((130, 170, 370, 355), fill=255)
        background_color = (210, 211, 213) if category == "transparent" else (239, 239, 239)
        image = Image.new("RGB", mask.size, background_color)
        if condition == "clutter":
            clutter = ImageDraw.Draw(image)
            for offset in range(20, 500, 35):
                clutter.line((0, offset, 512, offset - 30), fill=(160, 180, 150), width=3)
        if condition == "multiple-foreground":
            ImageDraw.Draw(image).rectangle((385, 95, 475, 200), fill=(180, 80, 30))
        if condition == "shadow":
            ImageDraw.Draw(image).ellipse((220, 320, 440, 420), fill=(45, 45, 45))
        color = (189, 197, 203) if category == "transparent" else (45, 90, 160)
        image.paste(color, mask=mask)
        if condition == "reflection":
            reflected = ImageOps.flip(mask).resize((512, 300))
            image.paste((175, 184, 192), (0, 312), reflected.crop((0, 0, 512, 200)))
        source, truth, important = scratch / "source.png", scratch / "truth.png", scratch / "details.png"
        image.save(source)
        mask.save(truth)
        details.save(important)
        add_case(root, source, f"synthetic-{object_name}", category, object_name, "synthetic", "synthetic controlled", f"synthetic {condition}", [condition], "Analytic drawing mask; not a real photograph or physical transparency test.", mask=truth, details=important if details.getbbox() else None)
    shutil.rmtree(scratch)
    return load_dataset(root)