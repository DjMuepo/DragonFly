# Controlled Real-AI Test Activation — Paid-Prediction Gate Implementation

Date: 2026-11-25
Repository: DjMuepo/DragonFly
Branch: `feature/staging-deployment`
Implementation commit: `a0d93d2` ("Add staging-only controlled paid-prediction gate for the real-AI test")
Prior readiness report: `2026-11-22-real-ai-controlled-run-readiness-check.md`
Scope: final controlled-inference safeguard before the owner-authorized single paid Hunyuan3D-2 reconstruction. No paid inference executed. No credentials accessed or exposed. No deploy, no merge, no production change.

## 1. Task scope

Implement and test, on `feature/staging-deployment` only:

1. A configurable, staging-only global paid prediction limit.
2. Restriction of the controlled test to exactly one authorized existing user account.
3. A global test allowance of exactly one paid prediction.
4. Persistence of the consumed allowance across backend restarts.
5. Rejection of unauthorized users and guest paid reconstruction requests.
6. Prevention of concurrent requests, automatic retries, and duplicate paid predictions.
7. Atomic reservation of the allowance before submitting a remote prediction, with no automatic restoration after ambiguous network failures.
8. Preservation of existing projects, authentication, editing, and export functionality.
9. Compatible HTTP request headers on the Replicate provider (explicit `User-Agent` + `Accept`; the default Python `urllib` User-Agent previously returned HTTP 403, the explicit headers returned HTTP 200 from the Render staging shell).
10. Mocked-inference tests for all safeguards and documentation of the exact Render environment variables.

## 2. Design

A new `PaidPredictionGate` enforces a **database-backed global allowance ledger** (`paid_predictions` table, migration `0002_paid_predictions.sql`) that lives in the same SQLite database as users/jobs on the persistent `/var/data` disk:

- **Startup (fail closed)** — `validate_paid_test_settings()` runs in `build_runtime()`:
  - `EYE_PAID_TEST_MODE=1` is refused outside local tests or the explicitly named `dragonfly-staging-geometry-backend` service (same environment fencing as the mock provider), so the gate can never be active on production.
  - `EYE_PAID_TEST_AUTHORIZED_USER_EMAIL` must be a syntactically valid email; `EYE_PAID_TEST_GLOBAL_LIMIT` must be an integer 0–10.
  - **Selecting the `replicate` provider on staging now requires the gate**: staging can no longer reach paid inference without the controlled-test configuration.
- **Request time (HTTP 403/429 before any job or upload is retained)** — `_create_geometry_job` calls `gate.authorize_request(owner)` whenever the resolved provider is `replicate-remote-gpu` and an image is present:
  - guest → 403 `paid_test_guest_forbidden`;
  - signed-in but not the authorized email → 403 `paid_test_unauthorized_user`;
  - allowance already consumed → 429 `paid_test_allowance_exhausted`.
  When the gate is disabled (non-staging environments), `authorize_request` is a no-op, so production behavior is unchanged.
- **Submission time (atomic, persisted, never auto-restored)** — `ReplicateGPUProvider.generate` calls `reserve_before_submission(job_id)` immediately before the prediction `POST`:
  - The reservation is a single `BEGIN IMMEDIATE` SQLite transaction (count non-released rows, compare to the limit, insert) — concurrent attempts serialize and exactly one can win the last unit.
  - The reserve additionally verifies the job belongs to the authorized account (defense in depth; guest- or untracked-job submissions are refused).
  - Nothing executes between the reservation and the `POST` dispatch, so **any failure from that point on — including an ambiguous network failure — leaves the allowance consumed**. There is no release/restore code path at all; recovery requires an operator decision (ledger row edit or a limit change) after reconciling the Replicate dashboard.
  - After the `POST` response, the Replicate prediction id is recorded on the reservation (`status=submitted`) for audit.
  - If `EYE_PAID_TEST_MODE=1` but the gate is not initialized, the provider refuses to submit (fail closed).
- **Retries/duplicates** — unchanged guarantees verified and extended: no retry loop exists anywhere around the prediction `POST`; `recover_interrupted()` marks interrupted jobs failed without re-running; `Idempotency-Key` replays return the existing job; and now the consumed ledger makes any further paid submission impossible regardless of the path taken.
- **Observability** — `GET /health` → `inference.paid_test` reports `{enabled, environment_allowed, global_limit, consumed, remaining, authorized_user_configured}` (no PII).
- **HTTP headers** — all Replicate API requests now send `User-Agent: DragonFly-GeometryBackend/0.4 (+https://github.com/DjMuepo/DragonFly)` and `Accept: application/json` (mesh downloads send the same UA with `Accept: */*`), replacing the default `Python-urllib/3.x` UA that was observed to be rejected with 403.

## 3. Changed files (commit `a0d93d2`)

- `eye-platform-alpha-geometry-backend/geometry-backend/app/paid_test_gate.py` — new gate module (validation, authorization, atomic reserve, ledger audit, provider hook, status).
- `eye-platform-alpha-geometry-backend/geometry-backend/app/persistence/migrations/0002_paid_predictions.sql` — new persisted allowance ledger table.
- `eye-platform-alpha-geometry-backend/geometry-backend/app/persistence/repository.py` — abstract ledger methods.
- `eye-platform-alpha-geometry-backend/geometry-backend/app/persistence/sqlite_repository.py` — atomic `reserve_paid_prediction` + ledger queries inside `BEGIN IMMEDIATE` transactions.
- `eye-platform-alpha-geometry-backend/geometry-backend/app/providers.py` — reservation immediately before the prediction `POST`, prediction-id audit recording, explicit `User-Agent`/`Accept` headers on API requests and mesh downloads.
- `eye-platform-alpha-geometry-backend/geometry-backend/app/environment.py` — `controlled_paid_test_allowed()` (same fencing as the staging mock).
- `eye-platform-alpha-geometry-backend/geometry-backend/app/runtime.py` — startup validation, gate construction/registration, `Runtime.paid_gate`.
- `eye-platform-alpha-geometry-backend/geometry-backend/app/main.py` — endpoint-level authorization with upload cleanup, `PaidTestGateError` response handler, `/health` gate status.
- `eye-platform-alpha-geometry-backend/geometry-backend/tests/paid_test_gate_test.py` — new mocked safeguard suite.
- `DRAGONFLY_RENDER_STAGING_GUIDE.md` — controlled-test environment variable documentation.
- `docs/codex-reports/2026-11-25-controlled-real-ai-test-activation.md` — this report (committed separately).

## 4. Exact Render environment variables (staging dashboard, `dragonfly-staging-geometry-backend` only)

**Activate the controlled test** (each save restarts the service; verify with `GET /health` afterwards — no spend):

| Variable | Value |
| --- | --- |
| `EYE_PAID_TEST_MODE` | `1` |
| `EYE_PAID_TEST_AUTHORIZED_USER_EMAIL` | *email of the one authorized existing account* |
| `EYE_PAID_TEST_GLOBAL_LIMIT` | `1` |
| `EYE_RECONSTRUCTION_PROVIDER` | `replicate` |
| `EYE_ENABLE_MOCK_PROVIDER` | `0` |
| `EYE_REPLICATE_MODEL_VERSION` | `tencent/hunyuan3d-2:b1b9449a1277e10402781c5d41eb30c0a0683504fb23fab591ca9dfc2aabe1cb` |

Leave unchanged: `REPLICATE_API_TOKEN` (already set in Render; never printed or copied), `EYE_ALLOW_PROCEDURAL_FALLBACK=0`, the four quota vars `=1`, `EYE_REPLICATE_TIMEOUT_SECONDS` (default 600), disk/`EYE_DATA_DIR`/signing/CORS settings. The backend now **fails startup** if `EYE_RECONSTRUCTION_PROVIDER=replicate` is set on staging without the three gate variables — a deliberate kill-switch default.

After restart, `GET /health` must show `"provider":"replicate"`, `"mock_enabled":false`, and `"paid_test":{"enabled":true,…,"global_limit":1,"consumed":0,"remaining":1,"authorized_user_configured":true}`.

**Deactivate (immediately after the run, success or failure):**

| Variable | Value |
| --- | --- |
| `EYE_PAID_TEST_MODE` | `0` (or remove) |
| `EYE_RECONSTRUCTION_PROVIDER` | `mock-test` |
| `EYE_ENABLE_MOCK_PROVIDER` | `1` |

(`EYE_PAID_TEST_AUTHORIZED_USER_EMAIL`, `EYE_PAID_TEST_GLOBAL_LIMIT`, and `EYE_REPLICATE_MODEL_VERSION` may remain; they are inert when the mode is off.) Confirm `GET /health` shows `"provider":"mock-test"`, `"mock_enabled":true`, `"paid_test":{"enabled":false,…}`. The consumed ledger row remains in the database on the persistent disk as a permanent record.

**Ambiguous-failure policy:** if the one allowance is consumed but the outcome is unclear (network error during/after submission), the gate does **not** restore it. Reconcile against the Replicate dashboard first; only then, if a second attempt is explicitly authorized, raise `EYE_PAID_TEST_GLOBAL_LIMIT` (max 10) — the ledger keeps all prior consumption counted.

## 5. Test commands and results (all mocked; zero network calls, zero paid predictions)

Backend — `eye-platform-alpha-geometry-backend/geometry-backend`, Python 3.12 (`.venv312`), `PYTHONPATH=. .venv312/bin/python tests/<name>.py`:

| Suite | Result |
| --- | --- |
| `tests/paid_test_gate_test.py` (new) | PASS — startup validation fails closed (production Render, wrong service name, missing email, invalid/oversized limit, replicate-on-staging without gate); guest 403, unauthorized 403, authorized pass; atomic reserve + QuotaExceeded when exhausted; 8-thread race → exactly one reservation; fresh repository on the same DB file stays exhausted (restart persistence); provider makes exactly one `POST` and keeps the consumed reservation after an ambiguous network failure (no retry, no restore); exhausted allowance blocks before any transport call; fail-closed when mode on but gate uninitialized; prediction id recorded on submitted reservation; `User-Agent`/`Accept`/`Authorization` headers asserted on the wire request; end-to-end FastAPI flow (guest 403 / intruder 403 / authorized 202 / idempotency replay with no second POST / 429 after consumption / health counters / procedural, auth, and projects endpoints still working) |
| `tests/core_integration_test.py` | PASS (auth, projects, durable jobs, artifacts, exports) |
| `tests/replicate_timeout_cancel_test.py` | PASS |
| `tests/reconstruction_fidelity_test.py` | PASS |
| `tests/staging_mock_test.py` | PASS (incl. static blueprint validation) |
| `tests/cors_security_test.py` | PASS |
| `tests/security_stabilization_test.py` | PASS |
| `tests/preprocessing_test.py` | PASS |
| `tests/smoke_test.py` | PASS |
| `tests/backup_restore_test.py` | PASS |
| `tests/editing_test.py` | **Pre-existing failure, unrelated**: fails identically on the base commit (`7d050c8`, verified via `git stash`) — the suite runs against the developer-local default `data/dragonfly.db`, whose accumulated guest daily quota makes its unauthenticated `/v1/geometry/generate` call return 429. Deterministic editor unit assertions in the same file pass. Not introduced or worsened by this change. |

Frontend — `eye-expo` (`npm run -s <suite>`): `test:api`, `test:history`, `test:projects`, `test:stabilization` — all PASS.

Skipped/blocked: `pytest` is not installed (suites are module-level-assertion scripts run natively, as in all prior reports); live header verification against Replicate was performed owner-side from the Render staging shell before this task (403 with default Python UA, 200 with explicit `User-Agent`+`Accept`) and is codified here but not re-run from this workspace (no token present, by design).

## 6. Deployment status

**Not deployed.** Committed and pushed to `feature/staging-deployment` only. Render staging still runs the previous build with `mock-test`; activating the controlled test requires the owner-side dashboard steps in section 4 plus a manual deploy of this branch. No merge to `main`, no production change, no Render setting touched, no paid prediction created.

## 7. Compliance statement

No paid inference was executed. No secret was read, printed, copied, or committed (`REPLICATE_API_TOKEN` never left Render; the blueprint still excludes it and `tests/staging_mock_test.py` re-verified that). No deployment, merge, or production modification was performed. All testing used mocked transports and local temporary databases.

## 8. Remaining issues

- `tests/editing_test.py` pre-existing local failure (stale guest daily quota in the committed-ignored local dev database) should be fixed by pointing the suite at a temporary `EYE_DATA_DIR` like the other integration suites.
- A hard USD spending cap remains unguaranteeable on Replicate; the gate caps *submissions* (exactly one), not the billed duration of that one prediction. The 600 s timeout-with-cancellation safeguard from `86cd824` remains the per-prediction cost bound.
- `/health` still does not expose the deployed commit SHA; deploy verification remains an owner-side dashboard glance.
- The consumed-allowance ledger is append-only by design; any authorized second test requires an explicit limit raise, which should itself be recorded in a follow-up report.
- External backup/restore attestation for staging remains outstanding (unchanged).
