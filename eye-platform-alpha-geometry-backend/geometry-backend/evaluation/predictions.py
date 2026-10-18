from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
import urllib.parse
import urllib.request
from pathlib import Path

from app.providers import ReplicateGPUProvider

from .isolation import digest
from .metrics import inspect_model


def write_json(path: Path, value: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


def cache_key(image: Path, model_version: str) -> str:
    settings = {"image_sha256": digest(image), "model_version": model_version, "input_parameters": {}, "adapter": "production_image_only_v1"}
    return hashlib.sha256(json.dumps(settings, sort_keys=True).encode()).hexdigest()


def prediction_plan(records: list[dict], root: Path, model_version: str, unit_cost: float | None) -> dict:
    if not model_version.strip():
        raise ValueError("An exact model/version must be supplied; no model is guessed.")
    if unit_cost is not None and (not 0 <= unit_cost < float("inf")):
        raise ValueError("Estimated cost per prediction must be finite and nonnegative.")
    entries = {}
    for record in records:
        for arm, prepared in record["pipelines"].items():
            key = cache_key(Path(prepared["input"]), model_version)
            existing = root / "cache" / key / "record.json"
            if existing.exists():
                state = json.loads(existing.read_text())
                if state["state"] == "complete":
                    model = existing.parent / state["model_file"]
                    if not model.is_file() or digest(model) != state["model_sha256"]:
                        raise ValueError("Cached output missing or changed; refusing to silently charge for regeneration.")
                disposition = state["state"]
            else:
                disposition = "uncertain_submission" if existing.parent.exists() else "new"
            entries.setdefault(key, {"key": key, "disposition": disposition, "cases": []})["cases"].append(f"{record['case']['id']}:{arm}")
    predictions = sum(entry["disposition"] == "new" for entry in entries.values())
    return {"mode": "plan_only", "provider": "replicate-remote-gpu", "model_version": model_version,
            "new_predictions": predictions, "estimated_cost_usd": predictions * unit_cost if unit_cost is not None else None,
            "cost_note": "Estimate only; model price unknown" if unit_cost is None else "User-supplied estimate; not an actual billed charge",
            "entries": list(entries.values())}


def authorize(plan: dict, execute: bool, allowed_predictions: int, budget: float | None, accept_unknown_cost: bool) -> None:
    if not execute or os.environ.get("DRAGONFLY_EVAL_PAID", "0") != "1":
        raise PermissionError("Paid execution disabled. Explicit --execute and DRAGONFLY_EVAL_PAID=1 are both required.")
    if allowed_predictions < plan["new_predictions"]:
        raise PermissionError("Authorized prediction count is below the displayed plan.")
    cost = plan["estimated_cost_usd"]
    if cost is None and not accept_unknown_cost and plan["new_predictions"]:
        raise PermissionError("Price unknown; explicit --accept-unknown-cost required.")
    if cost is not None and plan["new_predictions"] and (budget is None or budget < cost or not 0 <= budget < float("inf")):
        raise PermissionError("An explicit finite --budget-usd covering the estimate is required.")


def run_prediction(image: Path, root: Path, model_version: str, timeout_seconds: int = 660) -> dict:
    key = cache_key(image, model_version)
    directory = root / "cache" / key
    manifest = directory / "record.json"
    if directory.exists() and not manifest.exists():
        raise RuntimeError("Incomplete submission cache: inspect provider history before any manual retry.")
    state = json.loads(manifest.read_text()) if manifest.exists() else None
    if state and state["state"] == "complete":
        model = directory / state["model_file"]
        if not model.is_file() or digest(model) != state["model_sha256"]:
            raise ValueError("Cached GLB is missing or changed; refusing automatic regeneration.")
        return {**state, "local_model": str(directory / state["model_file"]), "reused_cache": True}
    if state and state["state"] not in {"submitted", "succeeded"}:
        raise RuntimeError("Prior request failed or submission outcome is uncertain. No automatic paid resubmission.")
    if os.environ.get("DRAGONFLY_EVAL_PAID", "0") != "1":
        raise PermissionError("Paid execution is disabled by default.")
    token = os.environ.get("REPLICATE_API_TOKEN", "").strip()
    if not token:
        raise PermissionError("Set REPLICATE_API_TOKEN in the shell; the evaluation tool never reads or prints private .env files.")
    if state is None:
        directory.mkdir(parents=True, exist_ok=False)
        state = {"state": "submitting", "provider": "replicate-remote-gpu", "model_version": model_version,
                 "input_parameters": {}, "input_sha256": digest(image), "started_at_epoch": time.time(),
                 "prediction_id": None, "estimated_cost_usd": None, "actual_cost_usd": None}
        shutil.copyfile(image, directory / "input.jpg")
        write_json(manifest, state)
        endpoint, body, _ = ReplicateGPUProvider._prediction_request(model_version, ReplicateGPUProvider._encode_image(image))
        prediction = ReplicateGPUProvider._request("POST", endpoint, token, body)
        state.update(state="submitted", prediction_id=prediction["id"], poll_url=prediction["urls"]["get"], prediction_status=prediction.get("status"))
        write_json(manifest, state)
    elif state["state"] == "submitted":
        prediction = ReplicateGPUProvider._request("GET", state["poll_url"], token, None, absolute=True)
    else:
        prediction = {"status": "succeeded", "output": state["output"]}
    deadline = time.monotonic() + timeout_seconds
    while prediction.get("status") not in {"succeeded", "failed", "canceled"}:
        if time.monotonic() >= deadline:
            raise TimeoutError("Prediction still pending; cache preserves its ID. Resume this prediction, do not submit another.")
        time.sleep(3)
        prediction = ReplicateGPUProvider._request("GET", state["poll_url"], token, None, absolute=True)
        state["prediction_status"] = prediction.get("status")
        write_json(manifest, state)
    state.update(prediction_status=prediction.get("status"), provider_metrics=prediction.get("metrics"))
    if prediction.get("status") != "succeeded":
        state.update(state="failed", error=str(prediction.get("error") or prediction.get("status")))
        write_json(manifest, state)
        raise RuntimeError(state["error"])
    if state["state"] != "succeeded":
        state.update(state="succeeded", output=prediction["output"], generation_duration_seconds=time.time() - state["started_at_epoch"])
        write_json(manifest, state)
    asset = ReplicateGPUProvider._find_mesh_url(state["output"])
    if not asset or urllib.parse.urlparse(asset).scheme != "https" or not urllib.parse.urlparse(asset).path.lower().endswith(".glb"):
        raise ValueError("Evaluation requires a returned HTTPS GLB; no procedural substitute or automatic conversion.")
    model = directory / "model.glb"
    if not model.exists():
        partial = directory / "model.partial"
        try:
            with urllib.request.urlopen(asset, timeout=60) as response, partial.open("wb") as output:
                size = 0
                for chunk in iter(lambda: response.read(1024 * 1024), b""):
                    size += len(chunk)
                    if size > 25 * 1024 * 1024:
                        raise ValueError("GLB exceeds the evaluation memory-safety download limit.")
                    output.write(chunk)
            partial.replace(model)
        finally:
            partial.unlink(missing_ok=True)
    with model.open("rb") as stream:
        if stream.read(4) != b"glTF":
            raise ValueError("Returned asset is not a GLB.")
    metrics = inspect_model(model)
    state.update(state="complete", output_url=asset, model_file=model.name, model_sha256=digest(model),
                 model_metrics=metrics, fidelity_verified=False, human_review={"outcome": "pending"})
    write_json(manifest, state)
    return {**state, "local_model": str(model), "reused_cache": False}