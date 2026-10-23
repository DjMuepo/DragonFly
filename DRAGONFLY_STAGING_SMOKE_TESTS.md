# DragonFly Staging Smoke Tests

These commands target an owner-provisioned staging backend only. They use the guarded deterministic `mock-test` provider and make no Replicate/paid AI calls. The script refuses to run unless `/health` reports a durable staging environment with mock inference enabled.

## Prerequisites

- `feature/staging-deployment` or a manually reviewed build is deployed to isolated staging services.
- A staging persistent disk is attached and verified. Backend uses `EYE_DATA_DIR`, `EYE_STORAGE_DURABLE=1`, `EYE_REQUIRE_DURABLE_STORAGE=1` and a stable `EYE_SIGNING_SECRET`.
- `EYE_APP_ENV=staging`, `EYE_ENABLE_MOCK_PROVIDER=1`, `EYE_RECONSTRUCTION_PROVIDER=mock-test`, exact staging `EYE_ALLOWED_ORIGINS`, and staging `PUBLIC_BASE_URL` are set.
- No `REPLICATE_API_TOKEN` is configured for this smoke run.
- Python environment has backend requirements installed (`Pillow` and backend dependencies). Install the isolated smoke-client dependency with `python -m pip install -r requirements-staging-smoke.txt` (`httpx`); it is not added to the production service image.

## Automated suite (no service required)

From repository root:

```sh
cd eye-platform-alpha-geometry-backend/geometry-backend
PYTHONPATH=. .venv312/bin/python tests/staging_mock_test.py
PYTHONPATH=. .venv312/bin/python tests/cors_security_test.py
PYTHONPATH=. .venv312/bin/python tests/security_stabilization_test.py
PYTHONPATH=. .venv312/bin/python tests/backup_restore_test.py
PYTHONPATH=. .venv312/bin/python tests/core_integration_test.py
```

`staging_mock_test.py` proves mock selection fails on a simulated production Render service and labels generated mock assets as `TEST DATA`. The other tests cover CORS, request caps, ownership, quotas/idempotency, artifact access and local backup integrity.

## Live staging workflow

Choose a private machine-local state path outside the repository. It contains the temporary smoke account password and bearer token and is created mode `0600`; protect/delete it after use.

```sh
cd eye-platform-alpha-geometry-backend/geometry-backend
umask 077
STATE_DIR=$(mktemp -d /tmp/dragonfly-staging-smoke.XXXXXX)
chmod 700 "$STATE_DIR"
STATE_FILE="$STATE_DIR/state.json"
PYTHONPATH=. python scripts/staging_smoke.py \
  --base-url https://<staging-backend-host> \
  --frontend-origin https://<staging-frontend-host> \
  --phase fresh \
  --state-file "$STATE_FILE"
```

The `fresh` phase verifies health/durable flags, staging mock mode, CORS allowed and denied origins, signup/login/session restoration, generation, TEST DATA labeling, user B isolation, save/reopen, edit, calibration, revision history and authenticated GLB/STL downloads. It writes the private state file only after completion.

Manually restart the staging backend from the Render dashboard (the script intentionally does not control Render). Then run:

```sh
PYTHONPATH=. python scripts/staging_smoke.py \
  --base-url https://<staging-backend-host> \
  --frontend-origin https://<staging-frontend-host> \
  --phase after-restart \
  --state-file "$STATE_FILE"
```

The `after-restart` phase checks session/project/revision/calibration/artifact persistence, downloads the GLB, logs out, verifies revocation, then deletes the bearer state file. If external backups are configured and a restore drill is attested, add `--require-backup`; otherwise the script will not claim that external backups exist.

Cleanup if a run is interrupted: securely remove the state file and directory; revoke the smoke account/session if still active and delete its staging project. Do not copy the state file into logs, tickets or the repository.

## Expected behavior and limitations

- Mock results show `provider_kind=mock_test` and a `TEST DATA` note. No Replicate API is called.
- A failed or restarted job is not automatically resubmitted.
- The live smoke script does not deploy, restart, provision a disk, configure backups, or test mobile-device UX. Device and browser UX remain separate manual gates.
