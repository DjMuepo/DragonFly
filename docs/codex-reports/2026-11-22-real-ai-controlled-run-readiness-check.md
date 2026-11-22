# Real AI Reconstruction — Final Readiness Check (Controlled Single Run)

Date: 2026-11-22 (19:47–20:00 UTC)
Repository: DjMuepo/DragonFly
Branch: `feature/staging-deployment`
Branch head at check time: `ab202e5` (report-only; backend source last changed by `86cd824`)
Prior report today: `2026-11-22-real-ai-reconstruction-final-readiness.md`
Owner authorization on record: exactly ONE paid Hunyuan3D-2 reconstruction, USD 2.00 maximum intended budget, acknowledging Replicate cannot guarantee a hard spending ceiling. Owner reports: new Replicate token configured in Render, auto-reload disabled, updated backend deployed, saved project survived deployment.
Scope: verification only. No paid prediction submitted. No Render settings changed. No deployment, merge, or production change. No secret accessed, printed, copied, or committed.

## Verdict

**READY for exactly one controlled real-AI reconstruction**, subject to two owner-side confirmations that cannot be performed from this workspace:

1. Deployed-commit confirmation in the Render dashboard (section 4 — one glance at the deploy event).
2. The read-only token check run inside Render Shell (section 3 — free, prints a status code only).

All workspace-verifiable items pass. The staging-only env flip and rollback are fully scripted in section 6.

## 1. Staging health and mock-test guardrail — PASS (live, 19:48 UTC)

- `GET https://dragonfly-staging-geometry-backend.onrender.com/health` → HTTP 200:
  `version=0.4.0-alpha`, `environment=staging`, `provider=mock-test`, `mock_enabled=true`, storage `ready=true`, `durable=true`, `database_integrity=ok`, `directories_ready=true`, migrations applied. Paid inference is currently unreachable.
- `https://dragonfly-staging-frontend.onrender.com/` → HTTP 200 (verified 19:33 UTC this session).
- `durable=true` live despite blueprint default `EYE_STORAGE_DURABLE="0"` is consistent with the owner's dashboard-level persistent-disk configuration (`/var/data`, `EYE_DATA_DIR=/var/data/dragonfly`) and with the owner's report that a saved project survived the redeploy.
- Known accepted gaps (unchanged): `external_backup_configured=false`, `restore_tested_attested=false`.

## 2. Model version vs. public listing — MATCH (verified 19:35 UTC today)

- Configured candidate: `tencent/hunyuan3d-2:b1b9449a1277e10402781c5d41eb30c0a0683504fb23fab591ca9dfc2aabe1cb`.
- https://replicate.com/tencent/hunyuan3d-2/versions lists `b1b9449a…` as **Latest** and the **only** version (author `@lucataco`, cog release `22.04`). Exact match with the configured value.
- Model page pricing unchanged: ~USD 0.11/run (~9 runs per USD 1), Nvidia L40S, typically ~118 s; predict time varies with inputs. One typical run ≈ 5.5% of the USD 2.00 budget; a worst-case 600 s timeout ≈ USD 0.585 of active time plus cancellation lag.
- `ReplicateGPUProvider` parses the `owner/model:version` format and extracts the version hash for `POST /v1/predictions`, so the string above is the correct `EYE_REPLICATE_MODEL_VERSION` value.

## 3. Secure read-only token verification procedure (owner-side, in Render)

Run inside **Render Dashboard → `dragonfly-staging-geometry-backend` → Shell** (the token already exists there as `REPLICATE_API_TOKEN`; it never leaves the service):

```sh
# Free, read-only; prints ONLY an HTTP status code. Never echo the variable.
curl -sS -o /dev/null -w '%{http_code}\n' \
  -H "Authorization: Bearer ${REPLICATE_API_TOKEN}" \
  https://api.replicate.com/v1/models/tencent/hunyuan3d-2/versions/b1b9449a1277e10402781c5d41eb30c0a0683504fb23fab591ca9dfc2aabe1cb

curl -sS -o /dev/null -w '%{http_code}\n' \
  -H "Authorization: Bearer ${REPLICATE_API_TOKEN}" \
  https://api.replicate.com/v1/account
```

- Expected: `200` and `200`. `401` means the token in Render is invalid/mis-pasted; `404` on the first call means the account cannot see this model version.
- Both are `GET` requests; Replicate does not bill reads. Do not run any `POST`.
- Prohibitions: never `echo $REPLICATE_API_TOKEN`, never pipe it to files or logs, never paste it outside Render, never commit it. This workspace deliberately holds no valid token (unauthenticated probe from here returns 401, re-confirmed 19:36 UTC today).

## 4. Timeout-cancellation safeguard in the deployed commit — PRESENT by construction; one-glance owner confirmation

- The safeguard (`86cd824`: `_cancel_prediction` helper, cancel-on-polling-deadline, `replicate_prediction_timeout` diagnostic event) is present at branch head — verified in `app/providers.py` (cancel call + event log at the timeout path, helper at `_cancel_prediction`).
- `git log 86cd824..HEAD -- eye-platform-alpha-geometry-backend/` is **empty**: the only commits after `86cd824` (`f27b098`, `ab202e5`) are report-only. Therefore **any** Render deploy of `feature/staging-deployment` performed after 2026-11-17 ships byte-identical backend code including the safeguard, regardless of which head was current.
- The running service cannot self-report its commit (`/health` exposes only the static `0.4.0-alpha` string), and Render's manual staging deploys do not appear in GitHub's deployments API (checked: only old `main` production deploys exist). **Owner confirmation (one glance):** Render Dashboard → `dragonfly-staging-geometry-backend` → Events/latest deploy → commit SHA must be `86cd824`, `f27b098`, or `ab202e5`. The owner's "updated backend deployed" statement is consistent with this but should be pinned to the SHA.
- The mocked-transport test re-ran clean just now: `tests/replicate_timeout_cancel_test.py` → PASS (exactly one prediction creation + one cancel POST on timeout; cancel failure annotates but does not mask; payloads without a cancel URL degrade gracefully).

## 5. Quotas, idempotency, duplicate-paid-submission prevention — VERIFIED in code

- **Quotas** (`app/persistence/sqlite_repository.py::create_job`): enforced inside the SQLite transaction at job creation — active-job count (`status IN ('queued','processing')`) against `EYE_MAX_ACTIVE_RECONSTRUCTION_JOBS_PER_USER` / `EYE_MAX_ACTIVE_GUEST_JOBS`, and a 24-hour rolling window count against `EYE_DAILY_RECONSTRUCTION_QUOTA_PER_USER` / `EYE_DAILY_RECONSTRUCTION_QUOTA_PER_GUEST`. All four default to **1** in code (`app/persistence/settings.py`) and are pinned to **"1"** in `deployment/render.staging.yaml`. Violations raise `QuotaExceeded` → HTTP **429** with `error_code` (`active_job_limit` / `daily_quota`), and any uploaded image/artifact is cleaned up.
- **Idempotency** (`app/durable_jobs.py::create` + `app/main.py::_create_geometry_job`): the `Idempotency-Key` header is scoped per owner (`owner_id` or `guest`). A replayed key returns the **existing** job with `replayed: true` — no second provider call, no second paid prediction. A reused key with a **different** request fingerprint → HTTP **409**. The dedup check runs both before and inside the insert transaction (`DuplicateError` → return existing), closing the race window.
- **Net effect for the controlled run:** with quotas at 1/1/1/1, at most one `generate` job can be active and at most one per 24 h per scope; the Idempotency-Key makes transport-level retries re-attach to the same job. Duplicate paid submissions are prevented at three layers (idempotency replay, active-job limit, daily quota).

## 6. Exact staging-only environment changes and rollback

All changes are **dashboard env-var edits on `dragonfly-staging-geometry-backend` only** (each save triggers a service restart; code is already deployed — no new deploy needed). Never touch production services, the blueprint file, or the frontend.

**Enable (test window only):**

| Variable | Value |
| --- | --- |
| `EYE_RECONSTRUCTION_PROVIDER` | `replicate` |
| `EYE_ENABLE_MOCK_PROVIDER` | `0` |
| `EYE_REPLICATE_MODEL_VERSION` | `tencent/hunyuan3d-2:b1b9449a1277e10402781c5d41eb30c0a0683504fb23fab591ca9dfc2aabe1cb` |

Leave unchanged: `EYE_ALLOW_PROCEDURAL_FALLBACK=0`, all four quota vars `=1`, `REPLICATE_API_TOKEN` (already set), `EYE_REPLICATE_TIMEOUT_SECONDS` (default 600), disk/`EYE_DATA_DIR`/signing/CORS settings.

After restart, confirm readiness **without spending**: `GET /health` must show `"provider":"replicate"` (and `mock_enabled=false`). The provider constructor fails fast if the token or model version is missing, so a healthy response in this state means configuration is complete.

**Run:** one original bottle photo (record its checksum), one signed-in workflow, one `Idempotency-Key`, exactly one logical job. On transport loss, poll the same job — never resubmit. Watch the Replicate dashboard; on backend timeout the safeguard auto-requests cancellation, but still verify the prediction reached a terminal state (`succeeded`/`failed`/`canceled`) and reconcile billed cost against USD 2.00.

**Rollback (immediately after the run, success or failure):**

| Variable | Value |
| --- | --- |
| `EYE_RECONSTRUCTION_PROVIDER` | `mock-test` |
| `EYE_ENABLE_MOCK_PROVIDER` | `1` |

(`EYE_REPLICATE_MODEL_VERSION` may remain set; it is inert under `mock-test`.) Then confirm `GET /health` shows `"provider":"mock-test"`, `"mock_enabled":true`, and `storage.durable=true` (saved projects persist across the restarts via the `/var/data` disk). If anything looks wrong mid-run, the same two-variable rollback is the kill switch — plus manual prediction cancellation in the Replicate dashboard.

## 7. Local/mock test results — all PASS, zero paid calls (this session, 19:36–19:52 UTC)

Backend (`eye-platform-alpha-geometry-backend/geometry-backend`, Python 3.12 `.venv312`, native script runners, each exit 0):

- `tests/core_integration_test.py` — PASS
- `tests/replicate_timeout_cancel_test.py` — PASS (re-run 19:52 UTC)
- `tests/reconstruction_fidelity_test.py` — PASS (local invariants only; no inference)
- `tests/staging_mock_test.py` — PASS incl. static blueprint validation (re-run 19:52 UTC)
- `tests/cors_security_test.py` — PASS
- `tests/security_stabilization_test.py` — PASS

Frontend (`eye-expo`, each exit 0): `test:api`, `test:history`, `test:projects`, `test:stabilization` — all PASS.

Skipped/blocked (unchanged rationale): `pytest` not installed (script runners used, as the suites are module-level-assertion scripts); Render dashboard reads and token-bearing checks are owner-side by design; the cancel-on-timeout path is validated against mocked transport only until the live run.

## 8. Compliance statement

No paid prediction was created or attempted. No Render setting was changed. No deployment or merge was performed. Production was not touched. No secret value was printed, read, copied, or committed; token presence was never queried beyond an unauthenticated (401) public probe from this workspace.

## Changed files

- `docs/codex-reports/2026-11-22-real-ai-controlled-run-readiness-check.md` (this report; committed separately).

No source, configuration, or deployment files were modified.

## Remaining issues

- Hard USD 2.00 cap remains unguaranteeable on Replicate (prepaid zero-balance cutoff with documented rare overrun is the best mechanism; auto-reload is reported disabled by the owner).
- Deployed-commit SHA and in-Render token validity each need the one-step owner confirmations in sections 3–4 before the run.
- `/health` does not expose the deployed commit; consider adding a build-SHA field in a future change to make deploy verification remote-checkable.
- External backup/restore attestation remains false in staging health.
- Local git-ignored `.env` still carries the revoked (401-dead) token string; owner hygiene cleanup recommended.
