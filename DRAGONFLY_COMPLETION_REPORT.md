# DragonFly Application Completion Sprint — Report

Date: 2026-10-21. Work branch: `feature/application-completion`, based on production `main` `2ac30ecb6e69dc06bb55d90556322474c87ea569`.

## Implemented Safe Fixes

- Print-preparation page now distinguishes a parametric-draft heuristic from slicer validation, removes novelty-derived print-confidence fallback, states print time is unmeasured, and exposes analyzer/export errors.
- Removed a dead STL/3MF alert placeholder; a real returned parametric STL URL is opened as a download.
- Nearby printer sample records are labeled demo-only, no location fallback coordinates are substituted, and no print-order action is offered when partner integration is absent.
- Nearby search now stops when location permission is unavailable instead of searching a fabricated location; print outcomes are explicitly self-reported.
- Legacy printer submit returns `not_integrated`/`submitted:false`; print-success events are not persisted without a verifiable printer job; client-supplied `is_paid` cannot grant subscription access.
- Alternate model edit screen uses deterministic supported commands and writes edits/calibration into existing revision history, requiring a real user-supplied dimension.
- Account service failures surface instead of being swallowed; capability text and launch-hub copy no longer claim generative AI or production-ready preview integrations where not implemented.
- Autosave no longer offers a local-only Pro toggle and discloses unavailable billing/storage.

These changes do not implement missing billing, storage, accounts, printer partners, slicers or AI editing. See `DRAGONFLY_APPLICATION_COMPLETION_MATRIX.md` and `DRAGONFLY_BETA_BLOCKERS.md` for workflow-by-workflow status and limitations.

## Changed Files

- `eye-platform-alpha-geometry-backend/geometry-backend/app/main.py` — fail closed for unimplemented slicer print preparation.
- `eye-platform-alpha-geometry-backend/geometry-backend/tests/editing_test.py` — assert print-prep endpoint returns HTTP 501 and does not claim checks.
- `api/app/services/printers.py` — no longer fabricates submitted request/ETA.
- `api/app/services/behavior_engine.py` — no fabricated print-success event.
- `api/app/services/subscription_gate.py` — no client-provided paid entitlement.
- `api/tests/test_unintegrated_workflows.py` — fail-closed behavior tests.
- `eye-expo/app/snap/ai-edit.tsx` — use supported deterministic prompts, user-entered calibration and revision history.
- `eye-expo/src/components/AiMeshEditor.tsx` — capability language aligned with deterministic support.
- `eye-expo/app/snap/nearby-printers.tsx` — label sample directory, require real location, disable fake ordering.
- `eye-expo/app/snap/print.tsx` — heuristic/error wording, STL URL download, self-reported print feedback, share errors, removed placeholder export.
- `eye-expo/src/lib/api.ts` — normalize relative STL download URLs against the API base.
- `eye-expo/app/autosave.tsx` — remove fake Pro toggle; explain billing/storage unavailable.
- `eye-expo/app/launch-hub.tsx` — label launch surfaces as previews.
- `eye-expo/app/account/index.tsx` — expose account and saved-design service failures.
- `eye-expo/app/autosave.tsx` — remove fake Pro toggle; explain billing/storage unavailable.
- `eye-expo/app/launch-hub.tsx` — label launch surfaces as previews.
- `eye-expo/app/snap/nearby-printers.tsx` — label sample directory, require real location, disable fake ordering.
- `eye-expo/app/snap/print.tsx` — heuristic/error wording, STL URL download, self-reported print feedback, share errors, removed placeholder export.
- `DRAGONFLY_APPLICATION_COMPLETION_MATRIX.md` — twelve-workflow implementation status and evidence.
- `DRAGONFLY_BETA_BLOCKERS.md` — prioritized blockers and release gates.
- `DRAGONFLY_APPLICATION_COMPLETION_MATRIX.md` — twelve-workflow implementation status and evidence.
- `DRAGONFLY_BETA_BLOCKERS.md` — prioritized blockers and release gates.
- `DRAGONFLY_COMPLETION_REPORT.md` — this report.

## Test Commands And Results

Backend, run from `eye-platform-alpha-geometry-backend/geometry-backend`:

- `PYTHONPATH=. .venv312/bin/python tests/smoke_test.py` — **PASS**.
- `PYTHONPATH=. .venv312/bin/python tests/editing_test.py` — **PASS**, including physical calibration, millimeter edits, Boolean edits, AI-mesh base source round-trip, GLB/STL bounds and fail-closed print-prep route.
- `PYTHONPATH=. .venv312/bin/python tests/preprocessing_test.py` — **PASS**, 12 MP EXIF orientation and memory-safe segmentation bypass.
- `PYTHONPATH=. .venv312/bin/python tests/reconstruction_fidelity_test.py` — **PASS**, local/mock diagnostics contract only; no real inference.
- `PYTHONPATH=api python -m unittest api.tests.test_unintegrated_workflows -v` from repo root — **PASS**, three fail-closed printer/print-success/subscription tests.

Frontend, run from `eye-expo`:

- `npm run test:history` — **PASS** (existing Node module-type warning only).
- `npm run typecheck` — **PASS**.
- `npm run build:web` — **PASS**.

Other checks:

- `git diff --check` — **PASS** before commit.
- No full pytest suite is configured; available script-style tests listed above were run.
- `web-landing`: `npm run build` — **BLOCKED**: `sh: 1: next: not found`. Dependencies were not installed and no unrelated package changes were made.
- No physical iPhone/Mobile Safari test was run for this branch. No paid inference or production API request was made.

## Commits And Branch

- Initial implementation commit: `41f41e7` (`Fail closed on unavailable beta integrations`).
- Report commit: separate follow-up commit, after the implementation hash was recorded here.
- Only `feature/application-completion` will be pushed. No merge or deployment is authorized or planned.

## Deployment Status

**Not deployed.** No Render config, production environment, or live application was changed. Current production source remains at base `2ac30ecb6e69dc06bb55d90556322474c87ea569`; the feature branch is isolated.

## Remaining Issues

- Account, saved projects, and authenticated sharing endpoints are not connected in root Render topology; legacy JSON-file services are prototypes.
- Printer partner/network, payments, real order tracking, slicer validation and physical print estimates remain absent. UI no longer claims a submitted request or integrated print check.
- Model edits are deterministic, finite and explicitly reject unsupported operations; quality/fidelity is not guaranteed by watertightness.
- Snap history is verified in the existing history test and persisted in browser storage; native persistence is not configured.
- Viewer is interactive on web; native viewer branch says interactive viewing is web-only. Physical mobile validation remains outstanding.
- Production AI outputs still require broad human-reviewed real-photo fidelity evaluation before public-beta promotion.

No new external service was introduced. No merge, deployment or paid inference occurred.
