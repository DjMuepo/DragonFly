# DragonFly Beta Security Checklist

Status: implementation checks verified in code/tests; production environment controls and device validation remain incomplete. No deployment performed.

## Browser/API boundary

- [x] CORS uses `EYE_ALLOWED_ORIGINS`; no wildcard fallback.
- [x] Root `render.yaml` names `https://dragonfly-frontend.onrender.com`; local/staging origins can be added as comma-separated explicit origins.
- [x] Requests from unapproved `Origin` are rejected; preflight rejects unapproved origins, methods and headers.
- [x] Required headers: `Authorization`, `Content-Type`, `Idempotency-Key`; methods are GET/POST/PUT/PATCH/DELETE/OPTIONS.
- [ ] Owner must verify the deployed frontend origin matches the configured origin before applying a staging blueprint.
- [ ] CORS is not authentication. Configure service ingress/rate limits separately.

## Authentication and authorization

- [x] Scrypt with per-password random salt; constant-time password verification.
- [x] Session tokens are random, hashed at rest, expiring and revocable.
- [x] Web token storage uses `sessionStorage`; native uses Expo SecureStore; app state uses separate storage. Legacy Zustand token snapshots are cleared and excluded from persistence.
- [x] Logout clears local account/project state and revokes the presented session when online.
- [x] Auth failures use bearer headers, not query parameters, including legacy `/v1/me` and `/v1/my-designs` endpoints.
- [x] Server-side project ownership checks cover list/open/rename/delete/cursor/revisions/source/verify/artifact/job operations.
- [x] Project model files are served from owner-authenticated routes; guest models retain the old public filename route for compatibility.
- [ ] Web `sessionStorage` remains script-accessible on the origin; review CSP/XSS protections or adopt a same-site cookie/BFF before broad public rollout.
- [ ] Add account recovery, email verification, session inventory and deletion policies.

## Abuse protection

- [x] Default caps: one active reconstruction per user/guest, one reconstruction per user/guest per rolling 24-hour window.
- [x] Caps and quotas are configurable and checked atomically in SQLite.
- [x] Default upload cap 15 MiB; bounded request bodies; credentials/project payloads are capped.
- [x] Provider request timeout defaults to 60 seconds; prediction deadline defaults to 600 seconds.
- [x] `Idempotency-Key` limits duplicate POSTs; concurrent same-key requests resolve to one job; changed payload returns 409.
- [x] Unknown provider/restart outcomes do not trigger automatic paid retries. UI requires acknowledgement before a new attempt.
- [x] Provider error logs omit raw exception strings/tokens; tests check token absence from a live server log.
- [ ] Login throttling is per-process/in-memory. Enable `EYE_TRUST_PROXY_HEADERS=1` only after confirming the trusted proxy overwrites `X-Forwarded-For`; multi-instance operation needs shared throttling.
- [ ] Add IP/global generation quotas, user-visible quota management and monitoring before opening signup broadly.

## Storage and files

- [x] Startup write probes, SQLite integrity check, startup migrations and safe legacy copy/conflict refusal.
- [x] Setting `EYE_REQUIRE_DURABLE_STORAGE=1` fails startup unless durable disk attestation and stable signing secret are set.
- [x] Artifact size/checksum validation and authenticated private file routes.
- [x] Backup archive covers SQLite DB, models, source photos, sidecars and migration marker; restore validates paths, hashes and SQLite integrity.
- [ ] Render persistent disk, stable secrets and external backup destination are not provisioned or tested.
- [ ] No external-backup restore drill, encryption-at-rest review, retention/erasure workflow or storage monitoring is configured.
- [ ] Existing legacy JSON API stores are not migrated to this repository; they remain undeployed/non-durable.

## Dependencies and validation

- [x] Non-breaking `npm audit fix` applied and SDK 56 lock matrix restored.
- [ ] Current Expo audit reports 20 findings: 17 high, 3 moderate, 0 critical. Remaining high findings include Expo/Metro/React Native paths whose listed fixes require breaking framework upgrades.
- [ ] No actual browser, iOS or Android device test was performed.
- [ ] No real Replicate prediction was run; all AI integration tests use a mock.
- [ ] No independent privacy, model/data-license, dependency, penetration, or production security review has been completed.
