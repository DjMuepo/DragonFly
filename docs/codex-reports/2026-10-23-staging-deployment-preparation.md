# Staging Deployment Preparation Report

Date: 2026-10-23
Branch: `feature/staging-deployment`
Base: `feature/beta-stabilization` at `2daf13134386991ae88324f2b63d9b7d5ab32ba5`
Implementation commits: `50ea66f66824134c11243b5d0d29bd6f9ce79dfc`, `45ac044` (disabled auto-deploy for the staging frontend as well as the backend).
Deployment: none. No merge. No paid inference. No Render services, disks or external backups were provisioned.

## Scope and implementation

- Added isolated `deployment/render.staging.yaml` with distinct `dragonfly-staging-*` names, `autoDeploy: false`, existing backend Dockerfile, Expo static build, no Replicate secret, and mock-only inference. Durable mode is initially `0` while durable startup is required, so staging intentionally will not start until an owner verifies/provisions a disk and changes it to `1`.
- Added `app/environment.py` guard: mock provider is only allowed in test/local staging, or on Render with `EYE_APP_ENV=staging`, `EYE_ENABLE_MOCK_PROVIDER=1`, `EYE_RECONSTRUCTION_PROVIDER=mock-test`, and the exact `RENDER_SERVICE_NAME=dragonfly-staging-geometry-backend`. Production Render services reject it.
- Added `StagingMockProvider`; results use provider kind `mock_test`, include `TEST DATA` labeling, and call only the deterministic geometry builder. Health reports environment/provider/mock status. Production Replicate provider behavior is unchanged.
- Added `scripts/staging_smoke.py` with fresh and after-restart phases: health and durable-storage gates, CORS allow/deny, signup/login/session restore, project ownership denial, mock reconstruction, edit, calibration, saved project/revision checks, private GLB/STL fetch, backend restart persistence, logout and revocation. Smoke state contains credentials and is restricted to a mode-0600 file outside the repository; no token is printed.
- Added isolated smoke-only `requirements-staging-smoke.txt` for `httpx`, avoiding a production image dependency.
- Added deployment, smoke and rollback documents with exact Render dashboard/environment/storage/backup requirements. Root production `render.yaml` was not changed.

## Files committed

- `deployment/render.staging.yaml`
- `eye-platform-alpha-geometry-backend/geometry-backend/app/environment.py`
- `eye-platform-alpha-geometry-backend/geometry-backend/app/main.py`
- `eye-platform-alpha-geometry-backend/geometry-backend/app/providers.py`
- `eye-platform-alpha-geometry-backend/geometry-backend/app/runtime.py`
- `eye-platform-alpha-geometry-backend/geometry-backend/requirements-staging-smoke.txt`
- `eye-platform-alpha-geometry-backend/geometry-backend/scripts/staging_smoke.py`
- `eye-platform-alpha-geometry-backend/geometry-backend/tests/staging_mock_test.py`
- `eye-expo/app/snap/result.tsx`
- `eye-expo/src/lib/geometryApi.ts`
- `DRAGONFLY_STAGING_DEPLOYMENT_PLAN.md`
- `DRAGONFLY_STAGING_SMOKE_TESTS.md`
- `DRAGONFLY_STAGING_ROLLBACK.md`
- This report.

## Tests and results

Backend, from `eye-platform-alpha-geometry-backend/geometry-backend`:

- `tests/staging_mock_test.py` — PASS; mock rejected on a production Render service identity, accepted only for the explicit staging service, result labeled test data.
- Root Blueprint structural check — PASS; exactly two staging service names, both `autoDeploy: false`, no production target names or Replicate token; `render.yaml` production definitions unchanged.
- `tests/cors_security_test.py` — PASS.
- `tests/security_stabilization_test.py` — PASS, including streamed body overrun abort.
- `tests/backup_restore_test.py` — PASS (local round trip only).
- `tests/preprocessing_test.py`, `tests/reconstruction_fidelity_test.py`, `tests/smoke_test.py`, `tests/editing_test.py`, `tests/core_integration_test.py` — PASS; reconstruction tests use a mock and make no Replicate call.
- `PYTHONPATH=. .venv312/bin/python -m py_compile scripts/staging_smoke.py` — PASS.
- `scripts/staging_smoke.py --help` — PASS.
- `PYTHONPATH=api python -m unittest api.tests.test_unintegrated_workflows -v` — PASS (3).

Frontend, from `eye-expo`: `npm run test:api`, `test:history`, `test:projects`, `test:stabilization`, `typecheck`, `build:web` — PASS. `web-landing npm run build` — PASS.

Manual local isolated smoke: started a local server with `EYE_APP_ENV=staging`, exact staging service name, temp `EYE_DATA_DIR`, `EYE_STORAGE_DURABLE=1`, required durable mode, local-only signing secret, localhost CORS origin, `EYE_ENABLE_MOCK_PROVIDER=1`, and `EYE_RECONSTRUCTION_PROVIDER=mock-test`. Fresh phase PASS: CORS, signup/login, session restoration, cross-user denial, mock generation, edit, 100 mm calibration, three revisions, GLB/STL. Server was stopped/restarted using the same temporary data directory. After-restart phase PASS: session, project, revisions, calibration and GLB persisted; logout invalidated the session. Temporary smoke session file was removed. No paid provider credentials were set.

`git diff --check` — PASS before commit.

## Owner prerequisites / limitations

- The Blueprint has no disk resource and does not assert a disk exists. Owner must attach a separate staging persistent disk, verify mount path, then set `EYE_DATA_DIR`, `EYE_STORAGE_DURABLE=1`, `EYE_REQUIRE_DURABLE_STORAGE=1`, and stable `EYE_SIGNING_SECRET` before the staging backend can start.
- Root `render.yaml` references production services. Use the new staging Blueprint only after reviewing service-name and change previews in Render. Auto-deploy is disabled. No service was created or deployed.
- External backup destination/schedule/restore drill remain unconfigured. Local backup tests do not prove external durability.
- Mock inference cannot validate real model fidelity or provider integration. No real Replicate call was made.
- Actual browser UI and physical iOS/Android testing remains outstanding.
- Existing npm audit findings from the stabilization sprint (20: 17 high, 3 moderate, 0 critical) remain; no breaking SDK upgrade was attempted.

## Deployment status

Prepared for owner review only. Not deployed, not merged and not public-beta ready. Production `render.yaml`, production services/secrets, `main`, and the experimental/infrastructure branches were not changed.
