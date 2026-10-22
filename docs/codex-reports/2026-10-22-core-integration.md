# Core Integration Sprint Execution Report

Date: 2026-10-22
Branch: `feature/core-integration` (from `feature/application-completion`)
Implementation commits: `7f053f6` (durable backend), `8532cd0` (Expo integration)
Documentation commit: `348aebb`
Deployment: none. Not merged. `render.yaml`, production configuration, `main`, `experimental/reconstruction-evaluation` and `feature/infrastructure-independence-foundation` were not modified.

## Scope

Integrate frontend and backend so users can register, authenticate, generate, save, reopen, edit and export models, with durable storage, ownership enforcement and restart-safe jobs. No paid inference was run.

## Changed files

Backend (`eye-platform-alpha-geometry-backend/geometry-backend`):
`app/main.py` (modified); new `app/accounts.py`, `app/api_routes.py`, `app/artifacts.py`, `app/durable_jobs.py`, `app/projects.py`, `app/runtime.py`, `app/persistence/__init__.py`, `settings.py`, `repository.py`, `sqlite_repository.py`, `migrate.py`, `migrations/0001_initial.sql`, `tests/core_integration_test.py`.

Frontend (`eye-expo`): `app/account/index.tsx` (rewritten), `app/index.tsx`, `app/snap/ai-edit.tsx`, `app/snap/reconstruct.tsx`, `app/snap/viewer.tsx`, `src/components/AiMeshEditor.tsx`, `src/lib/api.ts` (removed token-in-URL helpers), `src/lib/geometryApi.ts`, `src/lib/useSnapStore.ts`, `package.json`; new `src/components/ProjectPanel.tsx`, `src/lib/projectMapping.ts`, `src/lib/projectsApi.ts`, `src/lib/revisionFromResult.ts`, `tests/projectMapping.test.ts`.

Repository: `.gitignore` (runtime data); `DRAGONFLY_CORE_INTEGRATION_REPORT.md`, `DRAGONFLY_API_ROUTE_MAP.md`, `DRAGONFLY_PERSISTENCE_DESIGN.md`, `DRAGONFLY_REMAINING_BETA_BLOCKERS.md`.

## Implementation summary

- Extended the deployed geometry service with auth, projects, durable jobs and artifact tracking behind a `Repository` interface (SQLite on a persistent disk; checksummed migrations).
- Scrypt passwords, hashed expiring revocable session tokens, server-side ownership checks, HMAC-signed 15 minute file links for project files, removal of the public `/static` mount.
- Signed-in generation creates a project with the source photo; edits and calibration append immutable revisions; undo, redo and reset persist; stale edits are refused; failed or interrupted jobs fail closed and are never re-run.
- Expo: token client with idempotency keys and bounded polling, account and project management screen, save/reopen panel, revision metadata, STL export button.

## Test commands and results

From `eye-platform-alpha-geometry-backend/geometry-backend`, `PYTHONPATH=. .venv312/bin/python tests/<test>.py`:

- `preprocessing_test` PASS
- `reconstruction_fidelity_test` PASS (mock/local only)
- `smoke_test` PASS
- `editing_test` PASS (unmodified, covers calibration, units, export, base round-trip, print-prep 501)
- `core_integration_test` PASS, includes the restart phase in a second process

From the repository root: `PYTHONPATH=api python -m unittest api.tests.test_unintegrated_workflows` PASS (3 tests).

From `eye-expo`: `npm run test:history` PASS (existing Node module-type warning), `npm run test:projects` PASS, `npm run typecheck` PASS, `npm run build:web` PASS.

Manual: live `uvicorn` on a temporary data directory returned healthy `/health` with `storage.durable=true`, answered a CORS preflight allowing `Authorization` and `Idempotency-Key`, completed signup, `/v1/auth/me` and `/v1/projects`, and the session token was absent from the server log. `python -m app.persistence.migrate` applied `0001_initial` once and reported up to date on rerun.

## Not run or blocked

- Real Replicate reconstruction: forbidden (paid); a mock provider was used.
- Browser or device UI interaction, Mobile Safari, iPhone, Android: no environment available. UI was only type-checked and built.
- Postgres, object storage: not implemented.
- `web-landing` rebuild: unaffected by this change, not rerun.
- Render deployment and persistent disk provisioning: requires the owner.

## Remaining issues

See `DRAGONFLY_REMAINING_BETA_BLOCKERS.md`. Key items: persistent disk and secrets must be provisioned or data is lost on redeploy; single instance only; legacy sharing, printers, billing and admin features remain non-operational; web session token lives in `localStorage` and native sessions are not persisted; CORS is `*`; no password reset, verification, quotas or backups; no real-device or real-inference validation.

## Deployment status

Not deployed and not production ready. Ready for owner review and a staging deployment after the storage configuration in `DRAGONFLY_PERSISTENCE_DESIGN.md` is in place.
