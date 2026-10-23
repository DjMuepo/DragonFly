# DragonFly Staging Rollback

This procedure applies only to the isolated `dragonfly-staging-*` services. It does not authorize or change production. No rollback was executed because no service was deployed by this sprint.

## Before staging tests

- Keep staging `autoDeploy=false` until review.
- Record the previous staging frontend/backend commit and service settings before manual deploy.
- Confirm the staging disk and backups are separate from production.
- Ensure a recent staging DB/files backup exists before destructive migration or restore work. A local archive is not an external backup.

## Roll back a staging release

1. Disable public access to the staging frontend (or remove its staging-only route) and stop additional staging writes.
2. In Render, redeploy the prior reviewed staging commit to the staging frontend and backend services only. Do not select production service names.
3. If the database schema is backward-compatible, restore the prior staging app build and retain the current disk snapshot for diagnosis.
4. If data restoration is necessary, stop staging writes, verify the backup archive and SQLite integrity, then restore to a separate empty recovery target first:

   ```sh
   cd eye-platform-alpha-geometry-backend/geometry-backend
   PYTHONPATH=. python scripts/restore_storage.py /external-backup/dragonfly.tar.gz --target /var/tmp/dragonfly-recovery
   ```

5. Check `/health`, sessions, project ownership and representative GLB/STL/source reads against the recovery target before switching the staging service's `EYE_DATA_DIR`.
6. Keep the previous disk directory/volume intact until acceptance is complete. The script's `--replace` option renames an existing target to `.pre-restore-<timestamp>`; do not delete that rollback copy until explicitly approved.
7. Re-run `DRAGONFLY_STAGING_SMOKE_TESTS.md` with mock inference. Leave staging auto-deploy disabled until reviewed.

## Scope protections

- Never point a staging restore at production `EYE_DATA_DIR` or production backup.
- Do not modify root production services, DNS, production secrets, or production inference settings.
- Do not merge `feature/staging-deployment` into `main` as part of rollback.
- If staging accidentally references production storage/credentials, stop the staging service, preserve logs, and ask the service owner to rotate any exposed secrets. Do not print secrets into this report.
