# Reconstruction Evaluation (Experimental, Local Only)

This toolchain is not imported by FastAPI, copied into the production Docker image, or connected to the mobile application. It changes no production defaults, editing, calibration, history, validation, viewer, export, or Render configuration. Do not merge, push to the production branch, or deploy it as part of an evaluation run.

## Safety And Evidence

- All commands default to no inference. Never run a paid command without the user's explicit authorization for the displayed prediction count and cost estimate.
- `DRAGONFLY_EVAL_GRABCUT=0` (default) disables experimental isolation. `DRAGONFLY_EVAL_PAID=0` (default) disables paid execution independently.
- Baseline A calls `app.image_preprocessing.prepare_reconstruction_image` unchanged, with the current deployed `EYE_LOCAL_SEGMENTATION=0` memory profile. FAST/STANDARD/HIGH_QUALITY are image preparation modes, not Hunyuan accuracy guarantees.
- B uses the same prepared baseline image. Confidence below 0.70, multiple substantial regions, missing nearby edges, and segmentation failures select **byte-identical baseline A**, not another JPEG encoding.
- GrabCut works on a maximum 512-pixel working image; baseline preprocessing caps full images at 1024/1280/1536 pixels. It loads no rembg/U2Net or hosted segmentation provider. Low-confidence results do not reject a user's photo.
- Confidence is an uncalibrated diagnostic, not a probability of correctness. Components are not silently discarded. Symmetry/reflections are warning-only; no hardcoded cup crop or reflection clipping is performed. Thin-feature preservation is not guaranteed.
- Original photographs, private user metadata, caches, signed asset URLs, and generated reports belong in ignored `evaluation-data/` and `evaluation-runs/`, not Git. These contain private information: do not publish or commit them without consent. A report is not an authenticated sharing service.
- The source screenshot and earlier screenshot-derived cup proxy are not camera photographs. Mark them `screenshot_proxy`, never transparent-object ground truth. A previous successful model download is not evidence of fidelity.

## Setup And Synthetic Dataset

Run from `eye-platform-alpha-geometry-backend/geometry-backend` using the tested Python 3.12 environment. Dependencies reuse backend requirements; GrabCut lazily imports OpenCV supplied by the existing rembg runtime. If OpenCV is absent, the experimental command stops; do not add it to production just for this evaluation.

```bash
PYTHONPATH=. .venv312/bin/python -m evaluation.cli init --dataset ../../evaluation-data
DRAGONFLY_EVAL_GRABCUT=1 PYTHONPATH=. .venv312/bin/python -m evaluation.cli prepare \
  --dataset ../../evaluation-data --output ../../evaluation-runs/no-cost --isolation grabcut
```

`init` creates 11 **synthetic** images across opaque (bottle, mug), transparent (cup, container), reflective (utensil, glossy object), geometric (box, mechanical component), and irregular (shoe, toy, household object) categories. Conditions cover analytical transparency/low contrast, reflection, shadow, clutter, multiple objects, openings, handles, and thin structures. These drawings test mask/software behavior; they do not simulate real optical transparency or validate reconstruction accuracy.

Each dataset uses this structure:

```text
manifest.json                    version, case metadata and paths
case-id/original.jpg              byte-preserved import (or original.png)
case-id/expected_mask.png         optional full-resolution binary silhouette
case-id/important_details_mask.png optional handles, stems, laces or opening boundaries
```

Workers run serially in separate processes, recording per-case elapsed preprocessing time and process peak RSS. A worker measured at or above 512 MiB fails the run. Measurements describe the tested inputs and local runtime, not a guarantee for every image or a production concurrency certification. No app instance is used for these experiments.

## Add Photographs Without Code Changes

Export the actual photo from iPhone Photos, not a screenshot of DragonFly. JPEG/PNG with EXIF orientation are supported by existing Pillow preprocessing. HEIC requires a decoder not bundled by this tool; export as JPEG before import. Imported bytes and EXIF are preserved, and orientation is corrected only on prepared copies. State unknown lighting, background, or dimensions as unknown/null; do not guess them.

```bash
PYTHONPATH=. .venv312/bin/python -m evaluation.cli add \
  --dataset ../../evaluation-data --id my-mug --image /path/to/original.jpg \
  --category opaque --object 'ceramic mug' --kind photo \
  --lighting 'diffuse indoor light' --background 'matte contrasting surface' \
  --conditions thin-handle shadow --silhouette 'one mug including complete handle and opening' \
  --dimensions-json '{"height":95}' --attribution 'owner and consent/source license'
```

Add `--mask /path/to/silhouette.png --details /path/to/features.png` when annotations exist. Masks must match the full-resolution **EXIF-oriented** image dimensions and have white intended object pixels, black background (including reflections/shadows). Detail masks identify intended foreground features, not holes' interior pixels. Annotate only known ground truth, preserve holes and handles, and mark ambiguous transparent boundaries for human review. Do not derive ground truth from the candidate mask itself.

Metadata records category, object, evidence kind, lighting, background, reflection/transparency/other conditions, raw pixel dimensions, format, mode, EXIF orientation, SHA-256, known millimeter dimensions if available, expected silhouette description, import date, and attribution. The evaluation record adds test date and actual preprocessing/provider settings. Original checksums are verified on every run; existing IDs are never overwritten. Real photographed inputs without masks receive no invented segmentation score.

## Outputs And Metrics

Each case output contains the unmodified source, baseline A image, B image actually selected, raw candidate mask, isolated preview (possibly rejected), and `case.json`. `results.json` and `comparison.html` combine the results. The HTML includes original/input/mask previews, saved GLB links and optional model-viewer previews; model-viewer uses its usual public script CDN only when the report is opened. It performs no inference. For GLB viewing serve the report locally with a static HTTP server; file opening is sufficient for image/metric review.

- **Mask completeness**: retained annotated foreground / annotated foreground.
- **Background contamination**: predicted background pixels / predicted foreground pixels.
- **Silhouette IoU**: mask intersection / union with the annotated silhouette.
- **Important detail recall**: retained annotated feature pixels / annotated feature pixels.
- Candidate metrics and **selected input** metrics are separate. For fallback, selected input is the full baseline frame; completeness of 1.0 there is not successful isolation, because background contamination may be high.
- GLB inspection reuses existing mesh-validity and artifact diagnostics: counts, watertightness, winding, boundary/non-manifold edges, connected surfaces/solid bodies, degenerate faces, bounds, and warning heuristics. Bounds remain model units until independently calibrated; no synthetic millimeter claims are made.
- 3D visual similarity/silhouette consistency stay null without a known camera pose/correspondence. A matched front-view render alone cannot validate unseen surfaces. Fused duplicate/stacked geometry can evade connected-component checks.

## Paired Prediction Planning And Authorization

First run preprocessing and visually review both selected inputs. Supply the exact production model/version reference obtained from private configuration or existing prediction metadata; the tool never guesses a model or reads `.env`. It reuses `ReplicateGPUProvider._prediction_request`, `_encode_image`, `_request`, and `_find_mesh_url`, supplying **only image** just like current production. Both arms use identical model version/default parameters. Other provider settings must be added explicitly and identically in a future authorized change, not silently inferred here. Hunyuan output is stochastic; one pair alone cannot establish a general improvement.

```bash
DRAGONFLY_EVAL_GRABCUT=1 PYTHONPATH=. .venv312/bin/python -m evaluation.cli pair \
  --dataset ../../evaluation-data --output ../../evaluation-runs/pair \
  --case my-mug --isolation grabcut --model-version 'owner/model:EXACT_VERSION_ID' \
  --estimated-cost-per-prediction 0.10
```

This is **plan only**. It prints unique new predictions, cache states, and a user-supplied estimated cost. Omit the estimate if unknown: the price is explicitly unknown, never invented or fetched with a paid call. The example price is illustrative, not a verified Hunyuan price.

Only after explicit user authorization for that plan may a human/operator rerun with `DRAGONFLY_EVAL_PAID=1`, `--execute`, `--authorize-predictions N`, and `--budget-usd B` covering the estimate. With an unknown price, explicit `--accept-unknown-cost` is also necessary. Provide `REPLICATE_API_TOKEN` via the shell without printing it; never paste credentials into reports or commands in chat.

Paid synthetic/screenshot submissions additionally require `--allow-non-photo-inference`. This acknowledgement never makes a screenshot a valid camera-photo control. Do not use it to bypass missing real evidence.

Completed predictions cache by prepared input SHA-256, exact model reference, and production request configuration. Identical A/B fallback inputs share one prediction. Pending predictions retain their prediction ID and poll URL and can resume without a second POST. A submission with an uncertain response, failed prediction, changed cached model, or incomplete cache directory is **not** automatically resubmitted. Inspect provider history to reconcile it before any new paid authorization. Never delete a cache merely to bypass a failed gate.

Saved cache evidence includes prepared input, prediction ID/status, exact version, elapsed generation wall time (including resume delays), provider timing metrics when supplied, returned asset URL, original GLB/hash, mesh diagnostics, and unknown actual cost. Downloads are streamed and capped at 25 MiB; unsupported/non-GLB outputs stop rather than substitute procedural geometry. Signed output URLs may expire; downloaded files remain the regression evidence. Keep caches even after authorization is revoked.

## Saved Models And Human Review (No Inference)

```bash
PYTHONPATH=. .venv312/bin/python -m evaluation.cli inspect-model \
  --glb /path/to/saved.glb --output ../../evaluation-runs/saved-metrics.json
PYTHONPATH=. .venv312/bin/python -m evaluation.cli attach-model \
  --output ../../evaluation-runs/no-cost --case my-mug --arm A \
  --glb /path/to/saved.glb --input-sha256 PREPARED_ARM_SHA256 \
  --model-version EXACT_VERSION_OR_EXPLICIT_UNKNOWN --prediction-id KNOWN_ID
```

An attachment is labeled user-associated historical evidence, not an independently verified new prediction. If the input hash/version is unknown, use standalone `inspect-model`; do not fabricate a pair. For historical job `247188d3b473`, the DragonFly job ID is not the underlying Replicate prediction ID, and its screenshot input is not a camera source.

```bash
PYTHONPATH=. .venv312/bin/python -m evaluation.cli review \
  --output ../../evaluation-runs/no-cost --case my-mug \
  --reviewer 'reviewer-name' --outcome inconclusive --a-fidelity unknown --b-fidelity unknown \
  --notes 'Compare front/side/back against original; record lost handle, opening or reflected geometry.' \
  --artifacts missing-handle background-geometry
```

Review states are improved/regressed/mixed/inconclusive; each arm has explicit pass/fail/unknown visual fidelity. Human identity, date, artifacts, and notes are retained. Reviews survive unchanged preparation, but new input/model evidence resets them to pending. No confidence score automatically creates a human pass.

## Promotion Gates And Tests

Promotion remains blocked by default, including when mask or mesh metrics look good. Before recommending any production change, require paired **real photo** improvement across categories, no unacceptable losses of handles/openings/thin edges, maintained validity, acceptable measured memory/runtime/cost, and documented editing/calibration/mm/export/history/manufacturing plus Mobile Safari/iPhone regressions. Do not deploy based on one object or synthetic-only results. This tool does not merge or deploy anything.

```bash
PYTHONPATH=. .venv312/bin/python tests/evaluation_test.py -v
PYTHONPATH=. .venv312/bin/python tests/preprocessing_test.py
PYTHONPATH=. .venv312/bin/python tests/reconstruction_fidelity_test.py
PYTHONPATH=. .venv312/bin/python tests/smoke_test.py
PYTHONPATH=. .venv312/bin/python tests/editing_test.py
```

Prediction-transport tests use explicitly mocked responses, never paid calls; they test cache/provenance logic, not reconstruction fidelity. Existing frontend checks are `npm run test:history`, `npm run typecheck`, and `npm run build:web` from `eye-expo`. Browser/iPhone regressions need separate actual-device evidence and remain unverified until performed.