# DragonFly Beta Stabilization Report

Date: 2026-10-23
Branch: `feature/beta-stabilization`
Implementation commits: `004e7388346270f48f99e86485e8ac5e132ba180`, `99e33ba9f889dfae327f9f63880489cc47c1e54d` (security/recovery test refinements)
Deployment: not deployed. No merge. Production inference configuration and persistent storage were not changed.

## Outcome

The highest-priority code-level security and reliability changes in this sprint are implemented and covered by automated tests. The sprint does **not** make DragonFly ready for a controlled public beta: persistent storage and external backups are not provisioned, there was no browser/device test of the integrated flows, there are remaining npm advisories, and the legacy `api/` remains undeployed.

## Implemented

- Strict allowlisted CORS: `EYE_ALLOWED_ORIGINS`; rejected browser origins are blocked; the production frontend origin is in `render.yaml`; permitted methods/headers are enumerated.
- Authentication hardening: scrypt password hashes, expiring/revocable sessions, email+optional trusted-proxy-IP throttling, bounded throttle state, 64 KiB sensitive API body limit, and bearer headers rather than token URLs. Frontend session tokens use SecureStore on native and sessionStorage on web; old persistent token fields are cleared.
- Inference controls: one concurrent generation and one generation/day per account or guest by default, configurable upload/provider deadlines, atomic SQLite limits, conflict-safe cryptographic idempotency keys, job lookup after a lost response, bounded polling, no automatic restart rerun, and explicit confirmation before potentially paid retry after uncertain outcomes.
- Storage readiness: writable directory/startup DB integrity checks, migration checksums, durable-storage startup gates and health status, safe legacy artifact migration/conflict rejection, and local backup/restore scripts with DB integrity and per-file checksums.
- Project GLB/STL files now use owner-authorized routes and frontend bearer-header downloads; new private URLs contain no signatures/tokens.
- Visible UI actions relying on undeployed sharing/printer/feedback/draft-export APIs are gated; fake similarity matches were removed. Core capture, reconstruction, edit, calibration, save/reopen, revision and export flows remain available.
- Expo package versions are pinned to the previously working SDK 56 matrix; native session and app state dependencies are included.

## Verification

Backend suite, from `eye-platform-alpha-geometry-backend/geometry-backend`:

- `cors_security_test.py` — PASS.
- `security_stabilization_test.py` — PASS, including chunked upload overflow returning 413 before endpoint body processing completes.
- `backup_restore_test.py` — PASS, including migration marker, checksum tamper rejection and non-empty target refusal.
- `preprocessing_test.py`, `reconstruction_fidelity_test.py`, `smoke_test.py`, `editing_test.py` — PASS.
- `core_integration_test.py` — PASS, including auth, project ownership, private GLB/STL endpoints, concurrent caps/idempotency, quotas, restart recovery, missing artifacts, units and mocked reconstruction.
- `PYTHONPATH=api python -m unittest api.tests.test_unintegrated_workflows -v` — PASS, 3 tests.

Frontend, from `eye-expo`:

- `npm run test:api`, `npm run test:history`, `npm run test:projects`, `npm run test:stabilization` — PASS.
- `npm run typecheck`, `npm run build:web` — PASS.
- `web-landing`: `npm run build` — PASS.

No real Replicate calls, paid predictions, device tests or Render deployments occurred. Expo script tests emit Node module-type warnings; the web export emits the existing Expo Router Babel deprecation warning.

## Required owner actions / blockers

- Attach a persistent Render disk and configure the variables listed in `DRAGONFLY_RENDER_STAGING_GUIDE.md`. Without it, account/project/artifact data is not durable.
- Configure an external backup destination, schedule backups, and perform a restore from that destination before claiming backup readiness. Local archive round-trip is verified; external durability is not.
- Confirm Render's trusted forwarding header before setting `EYE_TRUST_PROXY_HEADERS=1`; otherwise the login limiter is per-account/per-process only.
- 20 npm audit findings remain (17 high, 3 moderate, 0 critical). Non-breaking fixes were applied; full remediation needs reviewed Expo/Metro/React Native dependency upgrades.
- Exercise session restoration and project artifact downloads in a browser and on actual iOS/Android devices. Tests here mock fetch/storage; no device was available.
- Replicate prediction recovery is deliberately fail-closed. The provider's prediction ID is not persisted as a resumable operation; restart/outcome uncertainty requires a user-confirmed new attempt and may incur another charge.
- Legacy account/sharing/printer/admin/billing endpoints in `api/` are not deployed. Their screens are gated or preview-only; do not expose them as operating services.

Readiness assessment: **not ready for public beta**. Suitable for review and a separately configured staging environment after the owner actions above; not deployed from this branch.
