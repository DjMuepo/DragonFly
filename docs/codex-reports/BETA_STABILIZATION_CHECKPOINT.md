# Beta Stabilization Sprint Checkpoint

Date: 2026-10-23
Branch: `feature/beta-stabilization` (created at core-integration tip `e843b895c68bb64848b2b30c91b2152e6d75879c`)
Implementation commit: `004e7388346270f48f99e86485e8ac5e132ba180`
Checkpoint report commit: recorded in the commit that adds this file.
Deployment: not deployed; no merge. `main`, `experimental/reconstruction-evaluation`, and `feature/infrastructure-independence-foundation` were not modified.

## Completed and committed

- Replaced wildcard CORS with `EYE_ALLOWED_ORIGINS`, strict origin rejection, explicit methods/headers, and the approved `https://dragonfly-frontend.onrender.com` origin in `render.yaml`.
- Added scrypt/IP-aware configurable login throttling, bearer-header auth to legacy `/v1/me` and `/v1/my-designs`, SecureStore tokens on native, sessionStorage on web, AsyncStorage native app-state persistence, token removal from general persisted state, and logout state cleanup.
- Added request-body caps, one active reconstruction per user/guest, one daily reconstruction by default, configurable provider/request deadlines, concurrent SQLite quota enforcement, cryptographically random idempotency keys, and recovery by idempotency header. Provider-uncertain/interrupted jobs are not retried automatically; the UI requests explicit confirmation before another potentially paid prediction.
- Added startup storage write/integrity checks, durable-storage/backup requirements, non-destructive migration from legacy geometry storage, checksummed backup/restore scripts, and database/model/source integrity tests.
- Project GLB/STL artifacts now use owner-authenticated routes and frontend bearer-header downloads instead of newly issued signed query URLs.
- Gated printer, sharing, community, feedback and draft-export actions that depend on undeployed services; removed fabricated similarity results and made photo classification optional. Core scan, reconstruction, edit, calibration, save/reopen, revision and export paths remain accessible.
- Pinned the Expo SDK 56 package matrix, added native storage/crypto packages, and applied semver-safe npm audit fixes.

## Files committed

- Backend: `api/app/main.py`, `render.yaml`, and `eye-platform-alpha-geometry-backend/geometry-backend/app/{accounts,api_routes,cors,durable_jobs,main,projects,providers,request_limits,runtime}.py`, `app/persistence/{repository,settings,sqlite_repository}.py`, backup/restore scripts, and stabilization/regression tests.
- Frontend: `eye-expo/app.json`, app layout/account/home/index/launch/print/reconstruct/result/results/viewer/community/printer screens, `src/components/AiMeshEditor.tsx`, session/artifact/geometry/store clients, `package.json`, `package-lock.json`, and API recovery tests.

## Tests and results

Backend, from `eye-platform-alpha-geometry-backend/geometry-backend`:

- `PYTHONPATH=. .venv312/bin/python tests/cors_security_test.py` — PASS (allowed/rejected origins, preflight, method/header allowlist, production origin in Render manifest).
- `PYTHONPATH=. .venv312/bin/python tests/security_stabilization_test.py` — PASS (IP/email throttle, request sizes, durable/secret/backup startup requirements, corrupt DB refusal, non-destructive legacy storage migration/conflict handling).
- `PYTHONPATH=. .venv312/bin/python tests/backup_restore_test.py` — PASS (SQLite, model, source and migration-marker round trip; tamper and non-empty-target rejection).
- `preprocessing_test.py`, `reconstruction_fidelity_test.py`, `smoke_test.py`, `editing_test.py` — PASS. These were run with temporary isolated data roots; fidelity is local/mock only.
- `core_integration_test.py` — PASS (auth expiry/revocation, ownership, private artifact access, quotas/concurrent idempotency, upload cap, generate/save/reopen/edit/calibrate/restart, GLB/STL integrity, failure/missing-artifact behavior). Provider is mocked; no Replicate request.
- From repository root: `PYTHONPATH=api python -m unittest api.tests.test_unintegrated_workflows -v` — PASS, 3 legacy safety tests.

Frontend, from `eye-expo` after `npm ci`:

- `npm run test:api`, `npm run test:history`, `npm run test:projects` — PASS.
- `npm run typecheck` — PASS.
- `npm run build:web` — PASS.
- `web-landing`: `npm run build` — PASS.
- Node emits an existing module-type warning on script tests; Expo emits a Babel deprecation warning during web export.

`git diff --check` — PASS before implementation commit.

## Dependency audit

`npm audit fix` (without `--force`) was run; the committed SDK was re-pinned to the prior working SDK 56 matrix after audit repair had temporarily produced an incompatible Expo 44 / React Native 0.88 installation. Final audit: 20 findings (17 high, 3 moderate, 0 critical). Remaining Expo/Metro/React Native dependency fixes require framework-level breaking upgrades. No forced SDK upgrade was kept. `npm ci`, typecheck and web build pass on the pinned lockfile.

## Remaining work and exact resume point

The implementation checkpoint is safe to resume from commit `004e738`; continue on this branch. The sprint is not complete and the branch is not production-ready.

1. Create the remaining requested root deliverables: `DRAGONFLY_BETA_STABILIZATION_REPORT.md`, `DRAGONFLY_SECURITY_CHECKLIST.md`, `DRAGONFLY_RENDER_STAGING_GUIDE.md`, and `DRAGONFLY_BETA_READINESS_MATRIX.md`.
2. Add and run frontend integration coverage for SecureStore/session restore, authenticated GLB/STL downloads, refresh-before-job-ID recovery, retry confirmation, and UI failure states. Current UI verification is typecheck/build plus API helper unit tests only.
3. Perform actual browser UI and native iOS/Android device testing. None was performed in this checkpoint.
4. Owner must provision a Render persistent disk and set `EYE_DATA_DIR`, `EYE_STORAGE_DURABLE=1`, stable `EYE_SIGNING_SECRET`, and appropriate `EYE_REQUIRE_DURABLE_STORAGE`. Production config was not changed to mount a disk or require it.
5. Configure an actual external backup destination and schedule `PYTHONPATH=. python scripts/backup_storage.py`; perform a restore from that external destination before attesting `EYE_BACKUP_EXTERNAL=1` and `EYE_BACKUP_RESTORE_TESTED=1`. Local round-trip tests do not demonstrate external durability.
6. Confirm Render's forwarded-client-IP behavior before setting `EYE_TRUST_PROXY_HEADERS=1`; otherwise login throttling is per account/process, not shared across instances. Multi-instance deployment needs a shared limiter and Postgres/object storage.
7. Remaining 20 npm audit findings need reviewed Expo/Metro/React Native upgrades; do not use `npm audit fix --force` without an SDK migration/test plan.
8. The old JSON-backed `api/` remains undeployed and non-durable. Sharing, billing, admin, invites, printer ordering, and other legacy screens remain unavailable/preview; route inventory/readiness signoff is unfinished.
9. No real Replicate inference, Render staging deployment, paid prediction, or external service test was made. In-progress external predictions cannot be recovered from Replicate after backend restart; jobs fail closed and are not automatically relaunched.

## Excluded from commit

Preserved untracked: `AGENTS.md`, two `ChatGPT Image` files, `evaluation-data/`, `evaluation-runs/`, `fidelity-evidence/`, and generated `eye-expo/dist/`. No credentials were staged. No merge or deployment occurred.
