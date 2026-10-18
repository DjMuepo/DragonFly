from __future__ import annotations

import argparse
import json
import os
import resource
import shutil
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image

from .dataset import CATEGORIES, add_case, initialize_fixtures, load_dataset, timestamp
from .isolation import SEGMENTATION_PROVIDERS, digest, prepare_baseline
from .metrics import inspect_model, mask_metrics
from .predictions import authorize, prediction_plan, run_prediction, write_json
from .report import write_report


def prepare_case(dataset: Path, output: Path, identifier: str, isolation: str, quality: str) -> dict:
    case = next(case for case in load_dataset(dataset) if case["id"] == identifier)
    directory = output / identifier
    directory.mkdir(parents=True, exist_ok=True)
    source = dataset / case["image"]
    original = directory / f"original{source.suffix}"
    shutil.copyfile(source, original)
    started = time.monotonic()
    baseline = prepare_baseline(original, directory / "A", quality)
    experimental = SEGMENTATION_PROVIDERS[isolation]().prepare(baseline, directory / "B")
    with Image.open(baseline.path) as image:
        size = image.size
    truth = dataset / case["expected_mask"] if case.get("expected_mask") else None
    details = dataset / case["important_details_mask"] if case.get("important_details_mask") else None
    pipelines = {}
    for arm, prepared in (("A", baseline), ("B", experimental)):
        pipelines[arm] = {
            "input": str(prepared.path), "metadata": prepared.metadata,
            "mask": str(prepared.mask) if prepared.mask else None,
            "preview": str(prepared.preview) if prepared.preview else None,
            "mask_metrics": mask_metrics(prepared.mask, truth, details, size),
            "selected_input_metrics": mask_metrics(None if prepared.metadata.get("fallback") else prepared.mask, truth, details, size),
            "prediction": None,
        }
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 if sys.platform != "darwin" else 1024 * 1024)
    record = {"case": case, "original": str(original), "evaluated_at": timestamp(),
              "settings": {"quality_mode": quality, "baseline": "existing_production_preprocessing", "isolation": isolation, "local_segmentation": False},
              "preprocessing_duration_seconds": time.monotonic() - started, "peak_rss_mib": peak,
              "memory_under_512_mib": peak < 512, "pipelines": pipelines,
              "human_review": {"outcome": "pending"},
              "promotion": {"eligible": False, "reason": "Human fidelity review, controlled real-photo comparisons across categories, and mobile/edit/calibration/export regression evidence are required. No automatic promotion."}}
    if digest(source) != case["sha256"] or digest(original) != case["sha256"]:
        raise ValueError("Source preservation check failed.")
    if not record["memory_under_512_mib"]:
        raise MemoryError(f"Evaluation worker peaked at {peak:.1f} MiB; do not promote.")
    previous_path = directory / "case.json"
    if previous_path.exists():
        previous = json.loads(previous_path.read_text())
        unchanged = all(previous["pipelines"][arm]["metadata"].get("image_sha256") == prepared["metadata"]["image_sha256"] for arm, prepared in pipelines.items())
        unchanged = unchanged and previous["settings"] == record["settings"] and previous["case"]["sha256"] == case["sha256"]
        if unchanged:
            record["human_review"] = previous.get("human_review", {"outcome": "pending"})
            for arm in pipelines:
                pipelines[arm]["prediction"] = previous["pipelines"][arm].get("prediction")
    write_json(directory / "case.json", record)
    return record


def prepare_dataset(dataset: Path, output: Path, identifiers: list[str] | None, isolation: str, quality: str) -> list[dict]:
    dataset, output = dataset.resolve(), output.resolve()
    if output == dataset or output.is_relative_to(dataset):
        raise ValueError("Keep output outside the source dataset to protect originals.")
    if isolation == "grabcut" and os.environ.get("DRAGONFLY_EVAL_GRABCUT", "0") != "1":
        raise PermissionError("GrabCut is disabled by default; explicitly enable DRAGONFLY_EVAL_GRABCUT=1.")
    cases = load_dataset(dataset)
    requested = set(identifiers or [case["id"] for case in cases])
    if requested - {case["id"] for case in cases}:
        raise ValueError("Unknown dataset case ID.")
    records = []
    backend = Path(__file__).resolve().parents[1]
    for case in cases:
        if case["id"] not in requested:
            continue
        subprocess.run([sys.executable, "-m", "evaluation.cli", "_case", "--dataset", str(dataset), "--output", str(output), "--case", case["id"], "--isolation", isolation, "--quality", quality], cwd=backend, check=True)
        records.append(json.loads((output / case["id"] / "case.json").read_text()))
    write_json(output / "results.json", records)
    write_report(output, records)
    return records


def paired(records: list[dict], output: Path, args) -> dict:
    plan = prediction_plan(records, output, args.model_version, args.estimated_cost_per_prediction)
    print(json.dumps(plan, indent=2), flush=True)
    if not args.execute:
        return plan
    if plan["new_predictions"] and any(record["case"]["kind"] != "photo" for record in records) and not args.allow_non_photo_inference:
        raise PermissionError("Non-photo evidence selected. Explicit --allow-non-photo-inference is required in addition to paid authorization; screenshots are not camera controls.")
    authorize(plan, args.execute, args.authorize_predictions, args.budget_usd, args.accept_unknown_cost)
    for record in records:
        for arm, prepared in record["pipelines"].items():
            prediction = run_prediction(Path(prepared["input"]), output, args.model_version)
            if (prepared.get("prediction") or {}).get("model_sha256") != prediction["model_sha256"]:
                record["human_review"] = {"outcome": "pending", "reason": "Model evidence changed."}
            cache_model = Path(prediction["local_model"])
            model = output / record["case"]["id"] / arm / "model.glb"
            shutil.copyfile(cache_model, model)
            prediction["local_model"] = str(model)
            prediction["estimated_cost_usd"] = args.estimated_cost_per_prediction
            prepared["prediction"] = prediction
            write_json(output / record["case"]["id"] / "case.json", record)
            write_json(output / "results.json", records)
            write_report(output, records)
    return plan


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local reconstruction quality evaluation. No paid inference by default.")
    commands = parser.add_subparsers(dest="command", required=True)
    initialize = commands.add_parser("init", help="Generate explicitly synthetic fixtures and masks")
    initialize.add_argument("--dataset", type=Path, required=True)
    add = commands.add_parser("add", help="Import an unmodified photo and capture metadata")
    add.add_argument("--dataset", type=Path, required=True)
    add.add_argument("--image", type=Path, required=True)
    add.add_argument("--id", required=True)
    add.add_argument("--category", choices=CATEGORIES, required=True)
    add.add_argument("--object", required=True)
    add.add_argument("--kind", choices=("photo", "screenshot_proxy", "synthetic"), required=True)
    add.add_argument("--lighting", required=True)
    add.add_argument("--background", required=True)
    add.add_argument("--conditions", nargs="*", default=[])
    add.add_argument("--silhouette", required=True)
    add.add_argument("--dimensions-json", type=json.loads)
    add.add_argument("--mask", type=Path)
    add.add_argument("--details", type=Path)
    add.add_argument("--attribution")
    for name in ("prepare", "pair", "_case"):
        command = commands.add_parser(name)
        command.add_argument("--dataset", type=Path, required=True)
        command.add_argument("--output", type=Path, required=True)
        command.add_argument("--case", action="append")
        command.add_argument("--isolation", choices=tuple(SEGMENTATION_PROVIDERS), default="baseline")
        command.add_argument("--quality", choices=("FAST", "STANDARD", "HIGH_QUALITY"), default="STANDARD")
        if name == "pair":
            command.add_argument("--model-version", required=True)
            command.add_argument("--execute", action="store_true")
            command.add_argument("--authorize-predictions", type=int, default=0)
            command.add_argument("--estimated-cost-per-prediction", type=float)
            command.add_argument("--budget-usd", type=float)
            command.add_argument("--accept-unknown-cost", action="store_true")
            command.add_argument("--allow-non-photo-inference", action="store_true")
    inspect = commands.add_parser("inspect-model", help="Inspect an existing GLB; never infer fidelity")
    inspect.add_argument("--glb", type=Path, required=True)
    inspect.add_argument("--output", type=Path, required=True)
    for name in ("review", "attach-model"):
        command = commands.add_parser(name)
        command.add_argument("--output", type=Path, required=True)
        command.add_argument("--case", required=True)
        if name == "review":
            command.add_argument("--outcome", choices=("improved", "regressed", "mixed", "inconclusive"), required=True)
            command.add_argument("--reviewer", required=True)
            command.add_argument("--notes", required=True)
            command.add_argument("--a-fidelity", choices=("pass", "fail", "unknown"), required=True)
            command.add_argument("--b-fidelity", choices=("pass", "fail", "unknown"), required=True)
            command.add_argument("--artifacts", nargs="*", default=[])
        else:
            command.add_argument("--arm", choices=("A", "B"), required=True)
            command.add_argument("--glb", type=Path, required=True)
            command.add_argument("--input-sha256", required=True)
            command.add_argument("--model-version", required=True)
            command.add_argument("--prediction-id")
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            print(json.dumps({"synthetic_cases": len(initialize_fixtures(args.dataset.resolve())), "paid_predictions": 0}))
        elif args.command == "add":
            case = add_case(args.dataset.resolve(), args.image.resolve(), args.id, args.category, args.object, args.kind, args.lighting, args.background, args.conditions, args.silhouette, args.dimensions_json, args.mask, args.details, args.attribution)
            print(json.dumps(case, indent=2))
        elif args.command == "_case":
            prepare_case(args.dataset.resolve(), args.output.resolve(), args.case[0], args.isolation, args.quality)
        elif args.command in {"prepare", "pair"}:
            records = prepare_dataset(args.dataset, args.output, args.case, args.isolation, args.quality)
            if args.command == "pair":
                paired(records, args.output.resolve(), args)
            else:
                print(json.dumps({"cases": len(records), "inference_performed": False, "report": str(args.output.resolve() / "comparison.html")}, indent=2))
        elif args.command == "inspect-model":
            write_json(args.output, {"source_model": str(args.glb.resolve()), "sha256": digest(args.glb), **inspect_model(args.glb)})
        else:
            output = args.output.resolve()
            records = json.loads((output / "results.json").read_text())
            record = next(record for record in records if record["case"]["id"] == args.case)
            if args.command == "review":
                if not args.notes.strip() or not args.reviewer.strip():
                    raise ValueError("Human review requires reviewer identity and substantive notes.")
                record["human_review"] = {"reviewer": args.reviewer, "reviewed_at": timestamp(), "outcome": args.outcome, "notes": args.notes, "A_fidelity": args.a_fidelity, "B_fidelity": args.b_fidelity, "artifacts": args.artifacts}
            else:
                prepared = record["pipelines"][args.arm]
                if digest(Path(prepared["input"])) != args.input_sha256:
                    raise ValueError("Saved model input hash does not match this prepared arm.")
                model = output / args.case / args.arm / "model.glb"
                shutil.copyfile(args.glb, model)
                prepared["prediction"] = {"evidence": "user-associated saved output, not newly inferred or independently provenance-verified", "local_model": str(model), "model_sha256": digest(model), "input_sha256": args.input_sha256, "model_version": args.model_version, "prediction_id": args.prediction_id, "generation_duration_seconds": None, "actual_cost_usd": None, "model_metrics": inspect_model(model)}
                record["human_review"] = {"outcome": "pending", "reason": "Saved model associated; human comparison required."}
            write_json(output / args.case / "case.json", record)
            write_json(output / "results.json", records)
            write_report(output, records)
    except (ValueError, PermissionError, RuntimeError, KeyError, StopIteration, OSError, subprocess.CalledProcessError) as error:
        parser.exit(2, f"Evaluation stopped: {error}\n")


if __name__ == "__main__":
    main()