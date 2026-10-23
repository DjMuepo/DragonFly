# DragonFly Render Staging Guide

This is an owner-run staging procedure. The sprint did not create services, attach a disk, change production credentials, merge, or deploy. The root `render.yaml` contains the production service names and must **not** be applied as a staging blueprint unchanged.

## 1. Create isolated staging services (owner action)

In Render, create a separate staging backend and static frontend from `feature/beta-stabilization` or a reviewed staging branch. Use unique service names, no production DNS, no production data directory, no shared disk, and disable automatic deploys until the initial review is complete. Preserve the existing production services for rollback.

Backend settings should match the repository's Docker service:

- Root: `eye-platform-alpha-geometry-backend/geometry-backend`
- Dockerfile: `./Dockerfile`
- Health check: `/health`
- Start command remains the Dockerfile command.

Frontend settings should match the static Expo service:

- Root: `eye-expo`
- Build: `npm ci && npm run build:web`
- Publish directory: `dist`
- `EXPO_PUBLIC_GEOMETRY_API_BASE`: staging backend public URL.

Root `render.yaml` currently contains the production origin and service names. Make a reviewed staging-only configuration with staging names/URLs; do not commit staging secrets.

## 2. Configure required backend environment

Required for a durable staging instance:

- `EYE_DATA_DIR`: mount path on the attached persistent disk (for example `/var/data/dragonfly`). Attach and verify the disk in the Render dashboard first.
- `EYE_STORAGE_DURABLE=1`: attests that the configured data directory is actually on persistent storage.
- `EYE_REQUIRE_DURABLE_STORAGE=1`: fail startup if durable storage or stable signing secret is missing.
- `EYE_SIGNING_SECRET`: generate a long random secret in Render's secret manager. Keep it stable across restarts; never place it in source, URLs or logs.
- `EYE_ALLOWED_ORIGINS`: exact comma-separated origin list; for staging use only the staging frontend origin (and explicitly approved local dev origins when needed).
- `PUBLIC_BASE_URL`: exact staging backend URL used in generated result references.
- `EYE_RECONSTRUCTION_PROVIDER=replicate`, `EYE_REPLICATE_MODEL_VERSION`, and `REPLICATE_API_TOKEN`: the code supports these, but setting a real token enables paid inference. Do not configure/use real inference until explicitly approved. Automated tests use a mock provider.

Safe defaults/optional controls (defaults shown):

- `EYE_MAX_ACTIVE_RECONSTRUCTION_JOBS_PER_USER=1`
- `EYE_MAX_ACTIVE_GUEST_JOBS=1`
- `EYE_DAILY_RECONSTRUCTION_QUOTA_PER_USER=1`
- `EYE_DAILY_RECONSTRUCTION_QUOTA_PER_GUEST=1`
- `EYE_UPLOAD_MAX_BYTES=15728640` (15 MiB)
- `EYE_REPLICATE_TIMEOUT_SECONDS=600`
- `EYE_REPLICATE_REQUEST_TIMEOUT_SECONDS=60`
- `EYE_SESSION_TTL_SECONDS=2592000` (30 days)
- `EYE_SIGNED_URL_TTL_SECONDS=900` (legacy compatibility only; new private project links use owner-authenticated routes)
- `EYE_TRUST_PROXY_HEADERS=1` only after verifying the Render proxy overwrites `X-Forwarded-For`. Default is off.

Do not set `EYE_BACKUP_EXTERNAL=1` or `EYE_BACKUP_RESTORE_TESTED=1` until a real separate backup destination and restore drill are complete. If backup is mandatory for a service, set `EYE_REQUIRE_BACKUP=1` after those checks.

## 3. Database initialization and health

At startup the service creates directories, checks writability, checks SQLite integrity and applies numbered migrations. Check `/health`:

- `storage.ready` must be true.
- `storage.durable` must be true for staging data expected to survive a restart.
- `storage.database_integrity` must equal `ok`.
- `storage.external_backup_configured` and `storage.restore_tested_attested` are informational attestations, not proof of actual external durability.

An existing legacy geometry DB/models/uploads are copied into an empty configured data directory. Conflicts cause startup to stop and preserve both copies. Snapshot the source before first mount migration.

## 4. Backup and restore

From the backend project root (with its Python environment and `PYTHONPATH=.`):

```sh
python -m app.persistence.migrate
python scripts/backup_storage.py --output /external/dragonfly/dragonfly-YYYYMMDD-HHMMSS.tar.gz
python scripts/restore_storage.py /external/dragonfly/backup.tar.gz --target /var/tmp/dragonfly-restore-test
```

Compare `/health`, project/artifact rows and representative GLB/STL/source-photo hashes in the restored test instance before setting restore-tested attestation. The restore script refuses a non-empty target unless `--replace` is given; with `--replace`, it renames the old target to a `.pre-restore-<timestamp>` rollback copy. Keep backups outside `EYE_DATA_DIR` and on a distinct failure domain. The local automated round-trip does not prove external backup durability.

## 5. Smoke/acceptance and rollback

Before any public traffic: verify CORS preflight only from the staging web origin; signup/login/logout/session expiry; project ownership across two users; generation with mocked inference; save/reopen/edit/calibrate/undo/export; interrupted-job no-rerun; missing-artifact behavior; backup/restore from the real destination; and mobile-browser/device behavior. Do not use production credentials/data for these tests.

Rollback staging by disabling the staging services and restoring their prior build/database snapshot. Keep production untouched. Do not change public DNS, merge to `main`, enable auto-deploy on production, or deploy this branch as part of this guide.
