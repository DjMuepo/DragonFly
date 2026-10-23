# Beta Stabilization Sprint Completion Report

Date: 2026-10-23
Branch: `feature/beta-stabilization`
Base checkpoint: `ec11f2124e3b6cd5b1d9735ff4b897ab7a0668ac`
Implementation: `004e7388346270f48f99e86485e8ac5e132ba180`, `99e33ba9f889dfae327f9f63880489cc47c1e54d`
Docs/report: separate follow-up commit.

## Scope and implementation

- CORS allowlist with exact production frontend origin, rejected-origin middleware, least-required methods/headers and preflight regression.
- Scrypt and expiring/revocable sessions; web sessionStorage/native SecureStore; logout cleanup; login email/IP throttling support with bounded process memory; trusted proxy headers opt-in.
- 64 KiB sensitive body cap, configured image size, atomic one-active/one-daily defaults, bounded provider deadlines, cryptographic idempotency, recovery by key/job, and no automatic re-run after restart or uncertain inference.
- Streamed request overflow throws before endpoint body handling completes; test verifies 413.
- Storage startup integrity/write checks, durable startup gate, safe legacy data conflict handling, backup/restore scripts and tested round-trip.
- Saved GLB/STL files use owner-authenticated project routes; frontend GLB/STL downloads send bearer headers. Session/recovery/artifact decisions are exercised by frontend integration helpers.
- Unavailable printer/sharing/feedback/legacy retrieval actions are gated; core flow remains.

## Implementation files

`api/app/main.py`, `render.yaml`; `eye-expo/app.json`, `_layout.tsx`, account/community/home/index/launch screens, snap nearby-printers/print/process/reconstruct/result/results/viewer screens, `src/components/AiMeshEditor.tsx`, `src/lib/{artifactClient,betaRecovery,geometryApi,sessionAdapter,sessionStorage,useSnapStore}.ts`, `tests/betaRecovery.test.ts`, `package.json`, `package-lock.json`; backend accounts/API/CORS/job/main/persistence/projects/provider/request-limit/runtime modules, backup/restore scripts, and security/integration tests.

## Tests

Backend from `eye-platform-alpha-geometry-backend/geometry-backend`:

- `PYTHONPATH=. .venv312/bin/python tests/cors_security_test.py` — PASS.
- `PYTHONPATH=. .venv312/bin/python tests/security_stabilization_test.py` — PASS, includes streamed over-limit request abort, config guards, throttle, legacy migration conflict and origin checks.
- `PYTHONPATH=. .venv312/bin/python tests/backup_restore_test.py` — PASS, DB/models/source/marker restore and tamper/target safety.
- `preprocessing_test.py`, `reconstruction_fidelity_test.py`, `smoke_test.py`, `editing_test.py`, `core_integration_test.py` — PASS; core integration includes auth, ownership, authenticated private GLB/STL, quotas, concurrency/idempotency, lifecycle/restart and mocked inference.
- Root: `PYTHONPATH=api python -m unittest api.tests.test_unintegrated_workflows -v` — PASS (3).

Frontend from `eye-expo`:

- `npm run test:api`, `test:history`, `test:projects`, `test:stabilization` — PASS. `test:stabilization` covers SecureStore/sessionStorage adapter behavior, `/auth/me` token restoration, auth headers for both GLB and STL, interrupted same-key retry, job recovery choices and paid retry confirmation.
- `npm run typecheck` — PASS.
- `npm run build:web` — PASS.
- `web-landing npm run build` — PASS.

Audit: 20 npm findings (17 high, 3 moderate, 0 critical) after non-forced fixes. No major Expo/React Native upgrade was attempted.

## Required environment and owner actions

See `DRAGONFLY_RENDER_STAGING_GUIDE.md`. Production root manifest still has no disk mount. Owner must attach/verify persistent disk and set `EYE_DATA_DIR`, `EYE_STORAGE_DURABLE=1`, stable `EYE_SIGNING_SECRET`, and then `EYE_REQUIRE_DURABLE_STORAGE=1`. External backup location, scheduled backup and restore drill are not configured; local test is not an external durability claim. Confirm trusted `X-Forwarded-For` before setting `EYE_TRUST_PROXY_HEADERS=1`.

## Remaining blockers and status

Public beta readiness: **NO**. No real browser or iOS/Android device flow was run; no Replicate request or paid inference was made; no Render deployment or external backup restore was performed. Unknown Replicate outcome after restart cannot be reconciled to a remote prediction ID; jobs fail closed and a new attempt needs explicit consent. Legacy JSON-backed `api/` endpoints remain undeployed; printers, billing, public sharing, admin and other legacy workflows are unavailable/preview. See `DRAGONFLY_SECURITY_CHECKLIST.md` and `DRAGONFLY_BETA_READINESS_MATRIX.md`.

Excluded from commits: untracked `AGENTS.md`, screenshots, evaluation datasets/runs, fidelity evidence and generated Expo `dist`. They remain untouched.
