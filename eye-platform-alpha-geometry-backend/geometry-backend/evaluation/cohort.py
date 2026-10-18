from __future__ import annotations

import json
import html
import math
from datetime import date
from pathlib import Path

from .dataset import add_case, load_dataset
from .isolation import digest
from .predictions import write_json


TEMPLATE = Path(__file__).with_name("real_world_cohort.json")


def initialize_cohort(root: Path) -> dict:
    manifest = root / "cohort.json"
    if manifest.exists():
        raise ValueError("Cohort already exists; no originals or pending slots were overwritten.")
    cohort = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    for item in cohort["objects"]:
        (root / item["input_directory"]).mkdir(parents=True, exist_ok=True)
    write_json(manifest, cohort)
    return validate_cohort(root)


def validate_cohort(root: Path) -> dict:
    cohort = json.loads((root / "cohort.json").read_text(encoding="utf-8"))
    expected = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    expected_cases = {item["id"]: item for item in expected["objects"]}
    identifiers = [item["id"] for item in cohort["objects"]]
    if cohort.get("version") != 1 or len(identifiers) != 6 or set(identifiers) != set(expected_cases):
        raise ValueError("The real-world cohort must contain exactly the six specified objects, without duplicates.")
    for field in ("provider", "inference_parameters", "pipeline_A", "pipeline_B", "segmentation_enabled_in_production"):
        if cohort["settings"].get(field) != expected["settings"][field]:
            raise ValueError("Cohort provider/settings must match the unchanged production comparison contract.")
    if cohort["settings"].get("quality_mode") not in {"FAST", "STANDARD", "HIGH_QUALITY"}:
        raise ValueError("Unsupported preparation mode.")
    directory = (root / cohort["dataset_directory"]).resolve()
    if not directory.is_relative_to(root.resolve()):
        raise ValueError("Cohort dataset must remain inside its root.")
    cases = {case["id"]: case for case in load_dataset(directory)} if (directory / "manifest.json").exists() else {}
    if set(cases) - set(expected_cases):
        raise ValueError("This cohort cannot include extra or substitute dataset objects.")
    for item in cohort["objects"]:
        if item["category"] != expected_cases[item["id"]]["category"]:
            raise ValueError("Unexpected category for a required object.")
        if item["input_directory"] != expected_cases[item["id"]]["input_directory"]:
            raise ValueError("Unexpected input directory for a required object.")
        if item["status"] == "pending":
            if item.get("image") or item.get("sha256") or item.get("camera_original_confirmed") or item["id"] in cases:
                raise ValueError("Pending slots must not claim imported photograph evidence.")
            continue
        if item["status"] != "ready":
            raise ValueError("Object status must be pending or ready.")
        case = cases.get(item["id"])
        if not case or case["kind"] != "photo" or not item.get("camera_original_confirmed") or not case.get("camera_original_confirmed"):
            raise ValueError("Ready objects require an explicitly confirmed original camera photograph, not screenshots, synthetic fixtures, or saved meshes.")
        for field in ("lighting", "background", "visible_reflections", "transparency", "capture_date"):
            if not isinstance(item.get(field), str) or not item[field].strip() or item[field] != case.get(field):
                raise ValueError(f"Missing or inconsistent {field} for {item['id']}.")
        date.fromisoformat(item["capture_date"])
        if item["sha256"] != case["sha256"] or item["category"] != case["category"]:
            raise ValueError("Cohort and dataset provenance do not match.")
        if item["image"] != case["image"] or item["pixel_dimensions"] != case["pixel_dimensions"] or item["exif_orientation"] != case["exif_orientation"]:
            raise ValueError("Cohort image metadata does not match the imported photograph.")
    return cohort


def import_camera_photo(root: Path, identifier: str, source: Path, lighting: str, background: str, reflections: str, transparency: str, capture_date: str, confirmed: bool, dimensions: dict | None = None) -> dict:
    cohort = validate_cohort(root)
    item = next(item for item in cohort["objects"] if item["id"] == identifier)
    if item["status"] != "pending":
        raise ValueError("Original already imported; no overwriting is allowed.")
    if not confirmed:
        raise PermissionError("Visually verify the actual fresh camera photograph, then explicitly confirm it. File extensions/EXIF alone cannot prove camera provenance.")
    for value in (lighting, background, reflections, transparency):
        if not value.strip():
            raise ValueError("Capture conditions must be recorded explicitly; use unknown rather than inventing them.")
    date.fromisoformat(capture_date)
    dataset = root / cohort["dataset_directory"]
    original_hash = digest(source)
    case = add_case(dataset, source, identifier, item["category"], item["object"], "photo", lighting, background, item["conditions"], item["expected_silhouette"], dimensions=dimensions)
    case.update(visible_reflections=reflections, transparency=transparency, capture_date=capture_date, camera_original_confirmed=True)
    data = json.loads((dataset / "manifest.json").read_text())
    data["cases"] = [case if entry["id"] == identifier else entry for entry in data["cases"]]
    write_json(dataset / "manifest.json", data)
    item.update({key: case[key] for key in ("image", "sha256", "pixel_dimensions", "exif_orientation", "format", "mode", "lighting", "background", "visible_reflections", "transparency", "capture_date", "known_dimensions_mm", "camera_original_confirmed")})
    item["status"] = "ready"
    if digest(source) != original_hash or digest(dataset / case["image"]) != original_hash:
        raise ValueError("Original photograph preservation failed.")
    write_json(root / "cohort.json", cohort)
    return item


def cohort_plan(root: Path, model_version: str | None = None, unit_cost: float | None = None) -> dict:
    cohort = validate_cohort(root)
    model_version = model_version or cohort["settings"].get("model_version")
    unit_cost = unit_cost if unit_cost is not None else cohort["settings"].get("estimated_unit_cost_usd")
    if unit_cost is not None and (not math.isfinite(unit_cost) or unit_cost < 0):
        raise ValueError("Cost estimate must be finite and nonnegative.")
    pending = [item["id"] for item in cohort["objects"] if item["status"] == "pending"]
    return {
        "mode": "dry_run_only", "paid_predictions_executed": 0,
        "ready_photos": 6 - len(pending), "missing_photos": pending,
        "planned_arms": 12, "maximum_new_predictions": 12,
        "actual_unique_predictions": None,
        "deduplication_note": "Actual count is calculated from prepared image hashes and caches; confidence fallback may reuse A for B.",
        "provider": "replicate-remote-gpu", "model_version": model_version,
        "settings": cohort["settings"], "estimated_unit_cost_usd": unit_cost,
        "estimated_cost_for_12_usd": 12 * unit_cost if unit_cost is not None else None,
        "cost_formula": "12 * verified or user-supplied per-prediction price; no price inferred",
        "blocked_by": (["missing original camera photographs"] if pending else []) + (["exact production model/version not supplied"] if not model_version else []) + (["price unknown"] if unit_cost is None else []) + ["paid inference not authorized"],
        "comparison_criteria": {
            "automated": ["input hashes and identical provider settings", "annotated silhouette completeness/contamination/IoU when available", "important-detail mask recall when annotated", "watertightness, connected surfaces, non-manifold edges", "bounds in model units; millimeter scale remains unknown without calibration", "processing duration, memory and actual cost when available"],
            "human_required": ["recognizable silhouette and overall shape", "missing or duplicated geometry", "handles, openings, edges and small details", "reflection/background contamination", "side/back geometry and scale uncertainty", "no promotion from isolation confidence alone"],
        },
        "objects": [{"id": item["id"], "status": item["status"], "A": "unchanged production preprocessing", "B": "experimental isolation with exact-baseline fallback", "source_sha256": item["sha256"], "model_version": model_version, "inference_parameters": {}} for item in cohort["objects"]],
    }


def write_cohort_plan(root: Path, plan: dict) -> None:
    write_json(root / "dry-run.json", plan)
    rows = "".join(f'<tr><td>{html.escape(item["id"])}</td><td>{html.escape(item["status"])}</td><td>{html.escape(item["A"])}</td><td>{html.escape(item["B"])}</td><td>Not run</td></tr>' for item in plan["objects"])
    criteria = html.escape(json.dumps(plan["comparison_criteria"], indent=2))
    root.joinpath("preparation.html").write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Six-object comparison preparation</title><style>body{font:16px Georgia,serif;margin:24px;color:#202020}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccc;padding:10px}pre{white-space:pre-wrap;overflow-wrap:anywhere}table{display:block;overflow-x:auto}</style><h1>Real-camera comparison: preparation only</h1><p>No paid predictions executed. Missing originals are pending, never replaced with screenshots, synthetic fixtures, or historical models.</p><p>Budget: at most 12 predictions; actual cost requires an exact model/version and price. Baseline fallback may reduce unique inputs.</p><table><tr><th>Object</th><th>Photo</th><th>A</th><th>B</th><th>Fidelity</th></tr>' + rows + '</table><h2>Comparison criteria</h2><pre>' + criteria + '</pre><h2>Execution blockers</h2><pre>' + html.escape(json.dumps(plan["blocked_by"], indent=2)) + '</pre></html>', encoding="utf-8")