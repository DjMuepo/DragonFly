# Infrastructure Independence Foundation Implementation Report

Date: 2026-10-21.

## Scope And Branch

- Repository: `DjMuepo/DragonFly`.
- Working branch: `feature/infrastructure-independence-foundation`, created from freshly fetched `origin/main`.
- Production base: `2ac30ecb6e69dc06bb55d90556322474c87ea569`.
- **Exact implementation commit: `06582c6cc9add70d89237a5d3fbdde4326224f67`.**
- Existing independent evaluation branch: `experimental/reconstruction-evaluation` at `c32e590ba5244a9d484e2bbc1d3c564bec000a86`; preserved without merging or modifying it.
- This report is a separate commit so the implementation hash does not require a self-referential edit. Publication target is only `origin/feature/infrastructure-independence-foundation`; no force-push or history rewrite is authorized.

Task objective: prepare architecture, dependency/license evidence and an inactive self-hosted inference contract for eventual owner-controlled operation, while preserving the current Replicate/Render/mobile/edit/calibration/history/export behavior.

## Changed Files

| File | Implementation |
|---|---|
| `DRAGONFLY_DEPENDENCY_AUDIT.md` | Audit of active/legacy frontend, API, geometry, AI/weights, build/deployment, storage, identity, queue, catalog and external service dependencies; fees/restrictions/independent alternatives; explicit unverified scope |
| `DRAGONFLY_SELF_HOSTING_ARCHITECTURE.md` | Owner GPU/API/DB/object-storage/job/auth/network/backup architecture; current implementation gaps; adapter/worker protocol; security, resources, rollback and migration gates |
| `DRAGONFLY_PROPRIETARY_AI_ROADMAP.md` | Data provenance/rights, explicit user consent, ownership limitations, training governance/infrastructure, evaluation and transition criteria |
| `docs/dependency-audit/package-inventory-2026-10-21.json` | 674 active JS lock entries, three direct JS manifests, declared Python requirements and 74 installed Python distribution declarations; unknown metadata and audit limitations explicit |
| `scripts/audit_dependency_inventory.py` | Repeatable no-network inventory generator; no installations, secret reads or model imports |
| `eye-platform-alpha-geometry-backend/geometry-backend/app/local_inference_contract.py` | Standalone typed image/model/resource/status/error/GLB lifecycle and provider-neutral local GPU protocol; not wired to production selection |
| `eye-platform-alpha-geometry-backend/geometry-backend/tests/local_inference_contract_test.py` | Six CPU-only contract tests for inputs/hash/pixel bounds, license-review gate, resource values, failure states and limited GLB-container validation |
| This report | Task completion record, separately committed after implementation |

No existing tracked production runtime/configuration file was modified. In particular, provider selection, Replicate request body/polling, preprocessing, editing, physical units, frontend, requirements, Dockerfiles and Render configuration remain unchanged.

Unrelated existing untracked `AGENTS.md`, user screenshots, `evaluation-data/`, `evaluation-runs/`, `fidelity-evidence/` and generated `eye-expo/dist/` were preserved and excluded from commits. The instruction policy in `AGENTS.md` was read and followed, not overwritten.

## Implementation And Architecture Findings

- Existing synchronous `ReconstructionProvider.generate` already supports interchangeable engines; no production refactor was necessary.
- New local GPU definitions specify submission, typed status, cancellation and resource snapshots. They do not start a worker, load weights, choose a model or run GPU inference.
- Model identities require exact revisions and actual weight hashes; image validation preserves input bytes and checks format/size/hash/pixels. Commercial review is an explicit precondition, not an automated legal opinion.
- GLB validation is deliberately named `validate_container`: header/version/declared-length/hash checks do not prove scene validity, AI execution, fidelity or printability. The test container is explicitly synthetic and is not a real generated mesh or a procedural substitute presented as AI.
- Resource values use null when unmeasured. GPU OOM, cancellation, overload, distributed durability and true execution provenance remain responsibilities of the future adapter implementation.
- Current geometry jobs and artifacts are process-local/filesystem based; legacy PostgreSQL methods are placeholders, and JSON authentication/queue helpers are not a complete production-independent data plane.
- Runtime unpkg model-viewer loading and build/model download endpoints are independence dependencies in addition to Replicate/Render.

## Model-License Evidence

Primary license/model-card text and metadata were retrieved publicly on 2026-10-21. No checkpoint files were downloaded and no gated acceptance/login was attempted.

- TripoSR: MIT code plus explicit pretrained-model MIT declaration; pinned HF model-card revision documented. Best first licensing baseline, not a demonstrated fidelity winner.
- TRELLIS-image-large: MIT-declared weights/main code; `diffoctreerast` actual license prohibits commercial use. Full stack not commercially approved; FlexiCubes actual license inspected as Apache-2.0.
- TripoSG: MIT-declared shape weights/code; documented BRIA RMBG-1.4 auxiliary model is non-commercial without a purchased commercial agreement. DINOv2/other exact dependencies still need review.
- Hunyuan3D-2: actual Tencent community license includes EU/UK/South Korea exclusions, territorial/output/use conditions and an additional release-date MAU commercial permission threshold. Do not generalize those exact terms to all family versions or assume the private production version.
- SF3D: public community terms include commercial registration, USD 1M annual-revenue/affiliate conditions, attribution and enterprise transition. Exact pinned gated weight-license request returned **HTTP 401**; weight agreement acceptance remains unverified.
- Root repository ownership/contributor licensing, package/native binary notices, training-data rights, actual production model/version and hosted service terms remain review gates. No unconditional commercial/legal approval was granted.

## Commands And Actual Test Results

Backend working directory: `eye-platform-alpha-geometry-backend/geometry-backend`. Interpreter: existing `.venv312/bin/python` (Python 3.12).

| Command / check | Actual result |
|---|---|
| `PYTHONPATH=. .venv312/bin/python tests/local_inference_contract_test.py -v` | PASS, six tests. Initial run exposed Pillow PNG verify ordering; fixed locally by verifying before EXIF metadata inspection, then the same suite passed |
| `PYTHONPATH=. .venv312/bin/python tests/preprocessing_test.py` | PASS; 4032x3024 synthetic EXIF-oriented JPEG -> 960x1280 with segmentation bypassed; reported test-process peak RSS 118.0 MiB |
| `PYTHONPATH=. .venv312/bin/python tests/reconstruction_fidelity_test.py` | PASS, local invariants and mocked provider transport only; no real AI inference |
| `PYTHONPATH=. .venv312/bin/python tests/smoke_test.py` | PASS; procedural test fixture GLB/STL and geometry assertions, not AI quality validation |
| `PYTHONPATH=. .venv312/bin/python tests/editing_test.py` | PASS; existing typed editing, calibration/mm, GLB/STL export and base-revision tests |
| `npm run test:history` in `eye-expo` | PASS; existing undo/redo/reset history regression |
| `npm run typecheck` in `eye-expo` | PASS |
| `npm run build:web` in `eye-expo` | PASS; static web export; generated files excluded |
| `npm run build` in `web-landing` | BLOCKED/FAILED: **`sh: 1: next: not found`**. Legacy landing dependencies are not installed. No dependency installation or unrelated change attempted |
| `.venv312/bin/python scripts/audit_dependency_inventory.py --output docs/dependency-audit/package-inventory-2026-10-21.json` from repository root | PASS; 674 JS entries, 74 installed Python distributions, zero network requests from generator |
| Inventory structure and local document-link assertions | PASS; three required documents, referenced local inventory and schema counts verified |
| `get_errors` for new contract, tests and generator | No editor diagnostics reported |
| `git diff --cached --check` | PASS after removing one trailing space caught before the implementation commit |
| Protected-path diff against `origin/main` | Empty for all existing active backend/frontend/configuration paths checked |
| `git rev-parse main experimental/reconstruction-evaluation` and matching `git ls-remote` | Production/evaluation references remained at the recorded hashes before publication |

Existing non-blocking frontend warnings: Node module-type inference for the history test and deprecated `expo-router/babel`. These were not changed because they are outside this task.

## Checks Not Executed

- Real Replicate/Hunyuan inference: intentionally not run; paid inference prohibited. No API credits spent.
- GPU/local-model inference, GPU memory, cancellation/OOM/process recovery: not run; no `nvidia-smi` executable available, no GPU worker or weights provisioned. CPU contract checks do not establish GPU compatibility.
- Large model weight downloads/training: prohibited and not performed.
- Actual iPhone/Mobile Safari camera/viewer/calibration/edit/history/download flow: not run; frontend code was unchanged. Build/type tests are not actual-device validation.
- Fresh real-camera quality comparisons: unavailable and not substituted with screenshots/synthetic fixtures. Separate experimental cohort remains intact.
- Legacy `api/` distributed DB/queue/auth end-to-end and legacy duplicate frontend: no relevant complete test suite/runtime installed or claimed; prototype behavior documented, not validated as a production platform.
- Container rebuild/offline air-gap/restore/network-failure/security penetration tests: not run; unchanged Dockerfile would fetch packages/models and is outside the no-weight-download scope.
- Gated SF3D weight-license acceptance and exhaustive native/transitive artifact/legal audit: not completed; unknowns explicitly documented.

## Deployment Status And Safeguards

**Not deployed. Not merged.** No Render configuration, service settings or deploy hooks were modified or invoked. Only the requested feature branch and this report may be pushed. Production `main` and the experimental evaluation branch are independent and unchanged. No new mandatory SaaS, paid segmentation provider, infrastructure purchase or recurring service was introduced.

The eventual adapter, data plane, trained model and production migration are proposals requiring separate owner authorization, legal/data review, actual GPU/quality/resource tests, durable storage/identity/backups, device parity and rollback evidence. Replicate remains available and unchanged.

## Remaining Issues And Recommended Next Step

1. Obtain the exact production model/version and service/legal terms without exposing credentials; review geographic/output/training rights with counsel.
2. Establish DragonFly ownership/contributor licensing and complete per-artifact software/model/dataset notices and commercial clearance.
3. Authorize owner GPU lab hardware/compute and reviewed model acquisition separately. Start with a pinned commercially reviewed baseline, not a claimed quality improvement.
4. Supply and consent fresh camera originals/ground truth, authorize any paid comparisons explicitly, and evaluate all required object categories, including transparent/reflective/thin cases.
5. Resolve legacy landing build dependencies in its own scoped task if that separate app is needed.
6. Implement/authenticate/durably test the future worker and data-plane design before switching any production traffic. Do not re-enable memory-heavy local segmentation on the 512 MB API.

This task delivers a tested contract and evidence-based architecture/audit foundation, not complete operational independence or successful self-hosted AI reconstruction.