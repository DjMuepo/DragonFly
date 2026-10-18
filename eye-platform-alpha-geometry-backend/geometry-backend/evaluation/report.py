from __future__ import annotations

import html
import json
from pathlib import Path
from urllib.parse import quote


def write_report(root: Path, records: list[dict]) -> Path:
    def asset(path: str | None, label: str, image: bool = False) -> str:
        if not path:
            return "Not available"
        location = quote(str(Path(path).relative_to(root)), safe="/")
        if image:
            return f'<a href="{location}"><img src="{location}" alt="{html.escape(label)}" loading="lazy"></a>'
        return f'<a href="{location}">{html.escape(label)}</a>'

    sections = []
    for record in records:
        rows = []
        for arm, prepared in record["pipelines"].items():
            prediction = prepared.get("prediction") or {}
            model = prediction.get("local_model")
            model_preview = "Inference not run"
            if model:
                location = quote(str(Path(model).relative_to(root)), safe="/")
                model_preview = f'<model-viewer src="{location}" camera-controls style="width:260px;height:240px"></model-viewer>' + asset(model, "Saved GLB")
            summary = {"preparation": prepared["metadata"], "candidate_mask_metrics": prepared.get("mask_metrics"), "selected_input_metrics": prepared.get("selected_input_metrics"), "prediction": {key: value for key, value in prediction.items() if key != "local_model"}}
            rows.append(f'<tr><th>{html.escape(arm)}</th><td>{asset(prepared["input"], "Submitted/prepared input", True)}</td><td>{asset(prepared.get("mask"), "Candidate mask", True)}{asset(prepared.get("preview"), "Isolated preview (may be rejected)", True)}</td><td>{model_preview}</td><td><pre>{html.escape(json.dumps(summary, indent=2))}</pre></td></tr>')
        case = record["case"]
        sections.append(f'<section><h2>{html.escape(case["id"])}: {html.escape(case["kind"])} / {html.escape(case["category"])}</h2><p>{asset(record["original"], "Unmodified original", True)}</p><p>{html.escape(case["expected_silhouette"])}</p><p>Human review: {html.escape(json.dumps(record.get("human_review", {"outcome": "pending"})))}</p><table><thead><tr><th>Pipeline</th><th>Input</th><th>Mask / rejected preview</th><th>Model</th><th>Measurements</th></tr></thead><tbody>{"".join(rows)}</tbody></table></section>')
    destination = root / "comparison.html"
    destination.write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>DragonFly reconstruction evaluation</title><style>body{font:15px Georgia,serif;margin:24px;color:#202020;background:#fff}table{border-collapse:collapse;width:100%}th,td{padding:10px;border:1px solid #ccc;vertical-align:top}img{display:block;max-width:240px;max-height:260px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}section{margin-bottom:40px}model-viewer{background:#eee}@media(max-width:800px){table,tr,td,th{display:block}}</style><script type="module" src="https://unpkg.com/@google/model-viewer@3.5.0/dist/model-viewer.min.js"></script><h1>Baseline versus experimental isolation</h1><p>Local evaluation only. Synthetic fixtures are not real-world validation. Watertightness is not visual fidelity. No automatic production promotion.</p>' + "".join(sections) + '</html>', encoding="utf-8")
    return destination