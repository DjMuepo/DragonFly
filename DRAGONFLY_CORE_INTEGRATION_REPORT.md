# DragonFly Core Integration Report

Branch: `feature/core-integration`, created from `feature/application-completion` (includes the web-landing build fix). Not merged, not deployed. `main`, `experimental/reconstruction-evaluation` and `feature/infrastructure-independence-foundation` were not touched. `render.yaml` is unchanged.

Implementation commits: `7f053f6` (backend), `8532cd0` (frontend). Documentation and execution report are committed afterward (see `docs/codex-reports/2026-10-22-core-integration.md`).

## Architecture decision

The geometry service already deployed on Render was extended instead of replaced. It now owns authentication, projects, durable jobs and artifact tracking. The legacy `api/` service is not deployed and its routes were left alone. See `DRAGONFLY_API_ROUTE_MAP.md`.

## What was implemented

**Storage** (`app/persistence/`): repository interface, SQLite implementation, checksummed SQL migrations, `python -m app.persistence.migrate`, settings with durability flags exposed in `/health`. Details and requirements in `DRAGONFLY_PERSISTENCE_DESIGN.md`.

**Accounts** (`app/accounts.py`): signup, login, logout, session restoration, scrypt hashing, hashed session tokens with expiry and revocation, failed-login throttle.

**Projects** (`app/projects.py`, `app/api_routes.py`): list, open, rename, delete, revision history, cursor persistence, original photo retrieval, artifact verification, saving guest results after sign-in. Ownership is enforced from the session on every route, job status and file download.

**Reconstruction and editing integration**: a signed-in generation creates a project with the source photo, model, STL and first revision. Edits and calibration with `project_id` (or a project model URL) append immutable revisions. A new edit after undo supersedes the redo tail without deleting it. Stale-revision edits return 409. Edits never call reconstruction. Failed reconstruction produces an explicit error, no project, no procedural substitute and the stored photo is removed.

**Jobs** (`app/durable_jobs.py`): jobs persist in the database, support idempotent retries via `Idempotency-Key`, interrupted jobs are failed on restart and never re-run, and `done` is only reported when the artifact exists.

**Existing behavior preserved**: the reconstruction pipeline code, Replicate provider, preprocessing, editor, calibration, units, GLB and STL export are unchanged. Existing regression tests pass unmodified. Removed: the public `/static` mount.

**Frontend** (`eye-expo`): bearer-token client with idempotency keys, bounded polling with transient-failure retry, session-expiry handling, rewritten account screen (sign up, log in, log out, session restore, project list, open, rename, delete with confirmation, loading and error states), `ProjectPanel` on the viewer and reconstruction screens (saved status, "Save to my projects", sign-in prompt, refresh of expiring file links, sync warnings), revision metadata (job and revision ids) on all revision sources, STL download in the viewer, and reopen-and-continue-editing through the existing viewer and editor. Undo, redo and reset persist the cursor server side.

## Files changed

Backend (`eye-platform-alpha-geometry-backend/geometry-backend`): `app/main.py` (modified), new `app/accounts.py`, `app/api_routes.py`, `app/artifacts.py`, `app/durable_jobs.py`, `app/projects.py`, `app/runtime.py`, `app/persistence/{__init__,settings,repository,sqlite_repository,migrate}.py`, `app/persistence/migrations/0001_initial.sql`, `tests/core_integration_test.py`. Root `.gitignore` (runtime data).

Frontend (`eye-expo`): modified `app/account/index.tsx` (rewritten), `app/index.tsx`, `app/snap/{ai-edit,reconstruct,viewer}.tsx`, `src/components/AiMeshEditor.tsx`, `src/lib/{api,geometryApi,useSnapStore}.ts`, `package.json`; new `src/components/ProjectPanel.tsx`, `src/lib/{projectMapping,projectsApi,revisionFromResult}.ts`, `tests/projectMapping.test.ts`.

## Tests

Backend, from `geometry-backend`, `PYTHONPATH=. .venv312/bin/python tests/<name>.py`:

| Test | Result |
|---|---|
| `preprocessing_test` | PASS |
| `reconstruction_fidelity_test` | PASS (mock/local invariants only) |
| `smoke_test` | PASS |
| `editing_test` | PASS (existing, unmodified) |
| `core_integration_test` | PASS (new, two processes for restart) |

`core_integration_test` covers: signup, login, logout, duplicate and weak input, password hash format, token revocation, expiry, forged tokens, login throttling; user A versus B isolation on projects, jobs, files, edits, rename, delete, cursor, source photo, verify; generate, save, reopen with source photo byte equality; edit, calibrate, reopen; calibration persistence (180 mm); STL height 180 mm and GLB 0.18 m; revision history, undo, redo, reset, superseded tail, stale edit refusal; idempotent replay with exactly one provider call and conflict on changed payload; failed reconstruction; missing artifact at job status, project open, download, verify and finalize; guest save with ownership checks; interrupted job recovery without inference; session, project, history and cursor survival across a process restart; editing after restart; sidecar restoration; project deletion removing files.

Other: `PYTHONPATH=api python -m unittest api.tests.test_unintegrated_workflows` PASS (3). Frontend from `eye-expo`: `npm run test:history` PASS, `npm run test:projects` PASS, `npm run typecheck` PASS, `npm run build:web` PASS. A live `uvicorn` run confirmed health, CORS preflight allowing `Authorization` and `Idempotency-Key`, signup, `/auth/me`, `/projects`, and that the token does not appear in the server log.

## Could not run

Real Replicate reconstruction (no paid calls allowed), browser or device UI testing (none available), Postgres (not implemented), Render deployment (not allowed), `web-landing` unchanged and not rebuilt in this sprint.

## Deployment readiness

Not ready for production. Code is ready for owner review and a staging deployment once a persistent disk and secrets are configured (see persistence design). Public beta blockers are in `DRAGONFLY_REMAINING_BETA_BLOCKERS.md`.
