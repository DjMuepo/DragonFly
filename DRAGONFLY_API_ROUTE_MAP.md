# DragonFly API Route Map

Branch `feature/core-integration`. Base URL for every route below: `EXPO_PUBLIC_GEOMETRY_API_BASE` (the `eye-geometry-backend` Render service). `api/` (legacy FastAPI) is **not deployed** by the root `render.yaml` and is not called by the integrated flow.

Auth: `Authorization: Bearer <token>`. Tokens are never accepted in URLs. Write endpoints accept an optional `Idempotency-Key` header.

## Deployed and integrated (geometry service)

| Method and path | Auth | Purpose |
|---|---|---|
| `GET /`, `GET /health` | none | Liveness. `/health` also reports `storage.durable` and configuration warnings. |
| `POST /v1/auth/signup` | none | Create account and session. 400 invalid input, 409 duplicate email. |
| `POST /v1/auth/login` | none | New session. 401 bad credentials, 429 after 5 failures per email per 15 min (per process). |
| `POST /v1/auth/logout` | required | Revokes the presented session. |
| `GET /v1/auth/me` | required | Session restoration. 401 when expired, revoked or unknown. |
| `GET /v1/projects` | required | List the caller's projects. |
| `POST /v1/projects` | required | Save finished guest jobs (`from_job_ids`, first must be a generation) as a project. |
| `GET /v1/projects/{id}` | owner | Project, active revisions, cursor, availability flags and 15 minute signed file links. |
| `PATCH /v1/projects/{id}` | owner | Rename. |
| `DELETE /v1/projects/{id}` | owner | Delete rows and files. |
| `PUT /v1/projects/{id}/cursor` | owner | Persist undo/redo/reset position. |
| `GET /v1/projects/{id}/revisions` | owner | Revision history. |
| `GET /v1/projects/{id}/source` | owner | Original uploaded photo. |
| `POST /v1/projects/{id}/verify` | owner | Re-hash every project artifact. |
| `POST /v1/geometry/generate-from-image` | optional | Reconstruction job. With a token the result becomes a project and the photo is kept. |
| `POST /v1/geometry/generate` | optional | Procedural prompt generation (existing behavior, never used as an AI fallback). |
| `POST /v1/geometry/edit`, `POST /v1/geometry/calibrate` | optional | Deterministic edit/calibration. Pass `project_id` or a project model URL to append a revision; ownership is enforced. |
| `GET /v1/geometry/jobs/{id}` | owner if the job is owned, open for guest jobs | Durable job status. `done` is only reported when the artifact exists. |
| `GET /v1/geometry/models/{file}` | signature or owner for project files; open for guest files | GLB/STL download. |
| `GET /v1/geometry/edit/capabilities`, `POST /v1/vision/classify` | none | Unchanged. |
| `POST /v1/geometry/prepare-print` | none | Returns 501. Slicer integration does not exist. |

Removed: the unauthenticated `/static` mount, which exposed models and uploads by path.

## Legacy API only (not deployed, not integrated)

About 100 routes in `api/app/main.py`: `/v1/vision/*`, `/v1/designs*` and `/v1/creators` (sharing), `/v1/printers/*`, `/v1/subscription`, `/v1/admin/*`, `/v1/invites/*`, `/v1/flows/*`, `/v1/behavior/*`, `/v1/training/*`, `/v1/jobs`, `/v1/challenges/*`, `/v1/world/*`, `/v1/structural/*`, `/v1/auth/*` (JSON-file accounts), `/v1/me`, `/v1/my-designs`. The frontend still contains calls to many of them (`eye-expo/src/lib/api.ts`); they fail against the deployed service and screens must be treated as non-operational. Printer submission, print-success recording and entitlement checks fail closed there (previous sprint). Sharing, payments and printer ordering were not exposed as working.

## Frontend resolution

- `src/lib/geometryApi.ts`, `src/lib/projectsApi.ts`: geometry service only.
- `src/lib/api.ts`: legacy helpers still target the same base and are unsupported; the token-in-query helpers were removed.
