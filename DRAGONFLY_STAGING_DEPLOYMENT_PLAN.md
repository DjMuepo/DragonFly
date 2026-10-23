# DragonFly Staging Deployment Plan

Date: 2026-10-23
Branch: `feature/staging-deployment` (source branch `feature/beta-stabilization`)
Status: configuration prepared; no Render service, disk, secret or deployment was created.

## Isolation and deployment safety

Use only `deployment/render.staging.yaml`. It creates:

- `dragonfly-staging-geometry-backend`
- `dragonfly-staging-frontend`

Both names differ from the production services in root `render.yaml` (`eye-geometry-backend`, `dragonfly-frontend`). Staging has `autoDeploy: false`; the root production manifest was not edited by this staging-preparation change. The staging manifest contains no Replicate token, no production DNS and no production data reference. It selects `mock-test`, has `EYE_ENABLE_MOCK_PROVIDER=1`, and starts with durable storage attestation off while requiring durability. Therefore the backend intentionally fails startup until an owner attaches/verifies its staging disk and changes the durable flag. This is a safety gate, not an accidental deployment failure.

Do not apply the root production Blueprint as staging. In Render, manually create/verify services or create a Blueprint from the staging file only. Confirm service names and URLs before accepting any change set.

## Render dashboard configuration

1. Create a separate staging environment/project. Review the proposed names above and `autoDeploy=false`. Do not attach production databases/disks or use production credentials.
2. Create the staging backend from the existing Dockerfile and root directory in the staging Blueprint. Before starting it with durable mode enabled, attach a new persistent disk and verify its mount path (the example is `/var/data`). No disk was provisioned by this sprint.
3. In the backend environment, configure:
   - `EYE_APP_ENV=staging`
   - `EYE_ENABLE_MOCK_PROVIDER=1`
   - `EYE_RECONSTRUCTION_PROVIDER=mock-test`
   - `EYE_DATA_DIR=<verified staging disk mount>/dragonfly`
   - `EYE_STORAGE_DURABLE=1`
   - `EYE_REQUIRE_DURABLE_STORAGE=1`
   - `EYE_SIGNING_SECRET=<long random secret entered via Render secret manager>`
   - `EYE_ALLOWED_ORIGINS=<exact staging frontend origin>`
   - `PUBLIC_BASE_URL=<exact staging backend URL>`
   - Conservative quota defaults from the Blueprint (1 active / 1 per day for user and guest).
4. Do not configure `REPLICATE_API_TOKEN` or `EYE_REPLICATE_MODEL_VERSION` for mock staging. Smoke requests must return `provider_kind=mock_test` and notes beginning `TEST DATA:`. Mock selection is rejected on Render unless `RENDER_SERVICE_NAME=dragonfly-staging-geometry-backend` and explicit staging variables are set. Production Render service names fail this guard.
5. Create the static frontend as `dragonfly-staging-frontend`, with `npm ci && npm run build:web`, publish `dist`, and `EXPO_PUBLIC_GEOMETRY_API_BASE=<staging backend URL>`. Confirm its assigned origin exactly matches `EYE_ALLOWED_ORIGINS`.
6. Keep auto-deploy disabled. Manually approve the first deploy only after inspecting the Render change preview. Root production service definitions and secrets must show no diff.

The staging Blueprint deliberately has `EYE_STORAGE_DURABLE=0` until the disk is verified. Update it to `1` only after the mount exists. It contains `EYE_REQUIRE_DURABLE_STORAGE=1` so accidental startup against ephemeral storage fails closed.

## Required non-inference settings

`EYE_ALLOWED_ORIGINS`, `PUBLIC_BASE_URL`, `EYE_DATA_DIR`, `EYE_STORAGE_DURABLE`, `EYE_REQUIRE_DURABLE_STORAGE`, `EYE_SIGNING_SECRET`, `EYE_APP_ENV`, `EYE_ENABLE_MOCK_PROVIDER`, and `EYE_RECONSTRUCTION_PROVIDER` are required for this staging profile. Render service name is part of the mock guard. No inference secret is required.

The code also supports quotas and timeouts; defaults are conservative:

- `EYE_MAX_ACTIVE_RECONSTRUCTION_JOBS_PER_USER=1`
- `EYE_MAX_ACTIVE_GUEST_JOBS=1`
- `EYE_DAILY_RECONSTRUCTION_QUOTA_PER_USER=1`
- `EYE_DAILY_RECONSTRUCTION_QUOTA_PER_GUEST=1`
- `EYE_UPLOAD_MAX_BYTES=15728640`
- `EYE_REPLICATE_TIMEOUT_SECONDS=600`
- `EYE_REPLICATE_REQUEST_TIMEOUT_SECONDS=60`

Do not set `EYE_TRUST_PROXY_HEADERS=1` until Render's forwarding behavior is verified.

## Persistent disk, migrations and backup

The process creates directories, checks write access and SQLite integrity, and applies checksummed migrations at startup. Inspect `/health` and require `storage.ready=true`, `storage.durable=true`, `database_integrity="ok"`.

Backups need a separate destination. After configuring `EYE_BACKUP_DIR` to an external disk/bucket mount and scheduling the script, run the commands in `DRAGONFLY_STAGING_SMOKE_TESTS.md`; perform a restore drill into a separate target. Only after verifying that remote destination and restore may an owner set `EYE_BACKUP_EXTERNAL=1` and `EYE_BACKUP_RESTORE_TESTED=1`. This sprint verified local archive/restore only.

## Verification gates

Run `DRAGONFLY_STAGING_SMOKE_TESTS.md` on the staging URLs. It is intentionally gated to durable storage and mock inference. Also test actual browsers and supported devices; no actual browser/device run is claimed here. Do not switch public DNS or promote staging to production from this branch.

## Rollback

Follow `DRAGONFLY_STAGING_ROLLBACK.md`. Preserve the staging database and backup archive for diagnosis; do not touch production services.
