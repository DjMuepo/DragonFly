# DragonFly Persistence Design

## Choice

SQLite (WAL, `synchronous=FULL`) stored on a persistent disk, behind a `Repository` interface (`app/persistence/repository.py`). Business logic in `accounts.py`, `projects.py` and `durable_jobs.py` depends only on that interface; `SqliteRepository` is the single implementation. A Postgres implementation can be added without touching application code. It was not written because no managed database exists and no credentials were available.

Reason: the current Render service is a single instance. A single-writer file database on an attached disk gives real durability with no new paid service. It does **not** support multiple instances or zero-downtime scaling.

## Durability requirements (owner action, nothing is deployed)

The default Render filesystem is ephemeral. Data survives only if all of these hold:

1. A Render persistent disk is attached to `eye-geometry-backend` (this changes the paid plan and `render.yaml`; not done here).
2. `EYE_DATA_DIR` points at the disk mount (for example `/var/data/dragonfly`).
3. `EYE_STORAGE_DURABLE=1` is set to assert the above. `/health` reports `storage.durable` and warnings; `EYE_REQUIRE_DURABLE_STORAGE=1` makes startup fail otherwise.
4. `EYE_SIGNING_SECRET` is set to a stable random value, otherwise signed file links stop working after a restart.
5. Disk snapshots or copies of `dragonfly.db` plus `models/` and `sources/` are scheduled; none exist yet.

Without 1 to 3 the service works but data is lost on redeploy, and `/health` says so.

## Layout under `EYE_DATA_DIR`

- `dragonfly.db`: database
- `models/`: GLB, STL and sidecar files (`.metadata.json` scale, `.features.json` editor state)
- `sources/`: original uploaded photos, kept only for authenticated projects
- `uploads/`: transient files (preprocessing input), deleted after use

If `EYE_DATA_DIR` is unset, behavior is backward compatible: models in `static/models`, database in `data/` (not durable, git-ignored).

## Schema (`app/persistence/migrations/0001_initial.sql`)

`users`, `sessions` (token hash, expiry, revoked_at), `projects` (owner, name, cursor_index), `artifacts` (kind, filename, size, sha256, owner, project), `jobs` (status, stage, error_code, result_json, idempotency key, owner scope), `revisions`.

- Revisions are immutable. The only mutable column is `superseded_at`, set when a new edit is made after an undo; superseded revisions are retained, never deleted. `(project_id, seq)` and `job_id` are unique, which also makes revision creation idempotent.
- `projects.cursor_index` is the position inside active (non-superseded) revisions, persisted by `PUT /cursor`, so undo/redo/reset survive restart.
- Each revision stores scale status, calibration, validation, features and the result metadata. Scale and feature sidecars are rebuilt from the database if the disk copy is missing, so calibration cannot silently revert to unknown. Units are unchanged: GLB in metres, STL in millimetres.
- Artifacts record size and SHA-256 at creation. Availability (existence and size) is checked on every project open and job status; `POST /verify` re-hashes.

## Security model

- Passwords: scrypt (N=2^14, r=8, p=1), random 16 byte salt, constant-time compare, dummy hash for unknown emails.
- Sessions: 32 byte random token returned once; only its SHA-256 is stored. TTL `EYE_SESSION_TTL_SECONDS` (default 30 days). Logout sets `revoked_at`. Expired or revoked tokens return 401.
- Ownership is checked server side from the session, never from client-supplied ids.
- Project files require a valid HMAC link (default 15 minutes, `EYE_SIGNED_URL_TTL_SECONDS`) or the owner's bearer token. Guest (unsaved) files stay addressable by name as before, because the original product contract used public model URLs.
- Credentials and tokens are not logged (verified in a live server log check).
- CORS remains `*` without credentials; tokens travel in headers, not cookies.

## Jobs

Jobs are rows, updated as the pipeline progresses. On startup any `queued` or `processing` job is marked `error` with `error_code=interrupted`. Nothing is resumed or re-run, because reconstruction can be paid inference. `Idempotency-Key` returns the existing job for the same owner and payload (409 for a different payload). Completion runs a finalizer that verifies the artifact and, for owned jobs, creates the project and revision in one step; a failure turns the job into an explicit error and no project is kept.

## Migrations

Numbered `.sql` files are applied in order, recorded with a checksum in `schema_migrations`, and refused if edited afterward.

- Apply: `python -m app.persistence.migrate` (also run automatically at process start).
- Add a change as `0002_name.sql`; never edit an applied file.
- Existing deployments have no previous database, so no data migration is required. Existing guest model files remain downloadable by their old URLs.

## Not covered

Postgres, object storage, multi-instance locking, a shared login rate limiter, backups, GDPR-style export, retention of superseded revisions and orphaned guest files, password reset and email verification.
