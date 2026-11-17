# Real AI Reconstruction Preflight — Token Rotation Follow-up

Date: 2026-11-17
Repository: DjMuepo/DragonFly
Branch: `feature/staging-deployment`
Implementation commit: `86cd824` (cancel-on-timeout cost safeguard + test; committed separately from this report)
Prior reports: `2026-10-31-real-ai-reconstruction-preflight.md`, `2026-11-16-real-ai-reconstruction-preflight-update.md`
Scope: continue preparation for exactly one controlled bottle-photo reconstruction on staging under a maximum authorized total Replicate spend of USD 2.00, after the owner rotated the Replicate API token and entered the replacement into the Render staging backend. No paid predictions were submitted. No deployment, merge, or production change was made. No secret values were accessed or printed.

## 1. Model and version — VERIFIED (public listing, 2026-11-17)

- Configured candidate (git-ignored local `.env` and prior reports):
  `tencent/hunyuan3d-2:b1b9449a1277e10402781c5d41eb30c0a0683504fb23fab591ca9dfc2aabe1cb`
- The public versions page (https://replicate.com/tencent/hunyuan3d-2/versions) lists version `b1b9449a…` as **Latest** and it is the only listed version (author `@lucataco`, cog release `22.04`, published ~1 year 9 months ago). Public availability is unchanged since the 2026-11-16 check.
- The backend's `ReplicateGPUProvider._prediction_request` accepts the `owner/model:version` format and extracts the version hash for `POST /v1/predictions`, so the string above is the correct `EYE_REPLICATE_MODEL_VERSION` value.
- Account-level availability (whether the owner's account can run this version) still CANNOT be verified from this workspace: the rotated token lives only in Render and must never be copied here. A free read-only check with the local `.env` token returned **HTTP 401** on both `GET /v1/account` and `GET /v1/models/tencent/hunyuan3d-2/versions/b1b9449a…` (status codes only; no values printed), re-confirming the old token is revoked and the rotation is effective from this side. The owner should run the same free `GET` once with the new token (owner-side, outside this repo) and confirm HTTP 200 before the paid test.

## 2. Pricing and the USD 2.00 ceiling — observed 2026-11-17

- Model page (https://replicate.com/tencent/hunyuan3d-2): approximately **USD 0.11 per run** (~9 runs per USD 1), Nvidia L40S hardware, predictions "typically complete within 118 seconds", predict time "varies significantly based on the inputs". Unchanged since 2026-11-16.
- Pricing page (https://replicate.com/pricing): L40S at **USD 0.000975/second** — unchanged.
- Timeouts are NOT billing limits. The backend's `EYE_REPLICATE_TIMEOUT_SECONDS` (default 600 s) polling deadline bounds how long the backend waits, not what Replicate bills. New in commit `86cd824`: on deadline expiry the backend now POSTs to the prediction's cancel URL before raising, which converts the timeout into a best-effort remote stop. Even so, cancellation is asynchronous and not guaranteed — the operator must reconcile actual billed cost in the Replicate dashboard after any timeout.
- Hard USD 2.00 enforcement: Replicate deprecated monthly spend limits for new customers on 2025-07-01. Current docs (https://replicate.com/docs/topics/billing/prepaid-credit, re-read 2026-11-17) state credit must be purchased upfront, usage deducts from the balance, and "as soon as your balance hits zero, we will prevent any new work from starting and shut down any infrastructure" — with the caveat that "in rare cases, a prediction may run over your credit balance", charged to the default payment method at month end. Auto reload minimums ($5 threshold / $15 reload) exceed the $2 authorization, so **auto reload must stay disabled**.
- Conclusion (unchanged): a low prepaid balance with auto reload off is the strongest available ceiling; it approximates but does not provably guarantee USD 2.00 because of the documented overrun case. One typical run (~USD 0.115) leaves wide headroom; a worst-case 600 s run is ≈ USD 0.585 of active time plus any cancellation lag.

## 3. Remaining configuration/code changes for one controlled reconstruction

Code change made in this task (commit `86cd824`):

- `eye-platform-alpha-geometry-backend/geometry-backend/app/providers.py`: `ReplicateGPUProvider` now cancels the remote prediction when the polling deadline expires (new `_cancel_prediction` helper; timeout error reports the actual configured seconds and the cancellation outcome; `replicate_prediction_timeout` diagnostic event logged). Previously the timeout abandoned a still-running, still-billing prediction.
- `eye-platform-alpha-geometry-backend/geometry-backend/tests/replicate_timeout_cancel_test.py` (new): mocked-transport verification that timeout triggers exactly one prediction creation plus a cancel POST, that cancellation failure annotates but does not mask the timeout error, and that payloads without a cancel URL degrade gracefully. No network, no paid calls.

Remaining changes are configuration-only, owner-side, for the test window:

1. Replicate billing (https://replicate.com/account/billing): confirm prepaid balance, keep auto reload OFF; if a legacy spend limit exists at https://replicate.com/account#limits, set it low.
2. Owner-side free token check: `GET /v1/models/tencent/hunyuan3d-2/versions/b1b9449a…` with the rotated token → expect HTTP 200.
3. Render dashboard (cannot be verified from this workspace): confirm the new `REPLICATE_API_TOKEN` exists on `dragonfly-staging-geometry-backend` only; confirm disk mount, `EYE_DATA_DIR`, signing secret, `PUBLIC_BASE_URL`, `EYE_ALLOWED_ORIGINS`, and the live quota values match the blueprint (1/day per user and guest, 1 active job each).
4. For the test window only, on the staging backend (never production): `EYE_RECONSTRUCTION_PROVIDER=replicate`, `EYE_REPLICATE_MODEL_VERSION=tencent/hunyuan3d-2:b1b9449a1277e10402781c5d41eb30c0a0683504fb23fab591ca9dfc2aabe1cb`, `EYE_ENABLE_MOCK_PROVIDER=0`; keep `EYE_ALLOW_PROCEDURAL_FALLBACK=0` and all quotas. The cancel-on-timeout safeguard requires the staging backend to be redeployed from a commit including `86cd824` before the test (deploy only with explicit owner authorization).
5. Local hygiene: the git-ignored backend `.env` still contains the revoked token string; replace or blank it before any local real-inference use (it is dead — 401 — so it poses no spend risk, only confusion).

No other code changes are required for one controlled reconstruction.

## 4. Guardrail state — mock ON, paid inference OFF (verified live 2026-11-17)

- `GET https://dragonfly-staging-geometry-backend.onrender.com/health`: HTTP 200, version `0.4.0-alpha`, `environment=staging`, `provider=mock-test`, `mock_enabled=true`, storage ready/durable, SQLite integrity `ok`, migrations applied. Real paid inference is NOT reachable: the provider is `mock-test` and the mock provider hard-fails outside explicitly enabled staging/test environments.
- `https://dragonfly-staging-frontend.onrender.com/`: HTTP 200.
- Blueprint `deployment/render.staging.yaml` still pins `EYE_RECONSTRUCTION_PROVIDER=mock-test`, `EYE_ENABLE_MOCK_PROVIDER="1"`, `EYE_ALLOW_PROCEDURAL_FALLBACK="0"`, `autoDeploy: false` ×2, no Replicate secret — statically re-validated by `tests.staging_mock_test`.
- Still outstanding in health: `external_backup_configured=false`, `restore_tested_attested=false`.

## 5. Safest staging-only test procedure (owner-gated; unchanged plus new safeguard)

1. Complete owner actions 1–3 of section 3; re-check model-page pricing immediately before submission.
2. Redeploy staging backend from a commit including `86cd824` (owner authorization required); flip the three provider env vars for the test window only (section 3.4).
3. Use one original bottle photo with recorded checksum; one signed-in workflow; one Idempotency-Key; exactly one logical job. On transport loss, recover the same job — never submit a new attempt.
4. During the run, watch the Replicate dashboard. If the backend times out, the new safeguard requests remote cancellation automatically; still verify the prediction reached a terminal state (`canceled`/`failed`/`succeeded`) in the dashboard, and cancel manually there if needed.
5. Capture prediction ID, terminal status, and actual billed cost; reconcile against the USD 2.00 authorization before any further action.
6. Immediately return staging to guarded mock mode (`EYE_RECONSTRUCTION_PROVIDER=mock-test`, `EYE_ENABLE_MOCK_PROVIDER=1`) and confirm `/health` shows `provider=mock-test`, `mock_enabled=true`.

## 6. Free/local validation — all PASS, no paid calls (2026-11-17)

Backend (`eye-platform-alpha-geometry-backend/geometry-backend`, Python 3.12 `.venv312`):

- `PYTHONPATH=. .venv312/bin/python tests/core_integration_test.py` — PASS.
- `PYTHONPATH=. .venv312/bin/python tests/replicate_timeout_cancel_test.py` — "replicate timeout cancel PASS" (new).
- `PYTHONPATH=. .venv312/bin/python tests/reconstruction_fidelity_test.py` — "reconstruction fidelity diagnostics PASS (local invariants only; no inference)".
- `.venv312/bin/python -m unittest tests.staging_mock_test` — "staging mock provider PASS" (includes static blueprint validation).
- `.venv312/bin/python -m unittest tests.cors_security_test` — "CORS security PASS".
- `.venv312/bin/python -m unittest tests.security_stabilization_test` — "security stabilization PASS".

Frontend (`eye-expo`): `npm run test:api` / `test:history` / `test:projects` / `test:stabilization` — all PASS.

Skipped/blocked checks:

- `pytest` not installed in `.venv312`; suites run with their native script/unittest runners as documented in each file.
- Render dashboard verification (new token presence, disk, live quotas): blocked — no Render credential in this workspace; owner-side only.
- Account-level Replicate availability check with the rotated token: blocked by design — the new token must not enter this workspace.
- No paid prediction was created; the cancel-on-timeout path was validated against a mocked transport only and will get its first live exercise (if ever) during the controlled test.

## Deployment status

Unchanged. Staging remains in guarded mock mode; the running staging backend predates commit `86cd824` and must be redeployed (owner-authorized) before the paid test to carry the cancel safeguard. Production untouched. No merge performed. This report authorizes nothing; the single paid test requires explicit owner approval after the owner-side verifications above.

## Remaining issues

- Provable hard USD 2.00 cap still impossible on Replicate's current billing model (prepaid zero-balance cutoff with documented rare overrun is the best available mechanism).
- Render-side secret/disk/quota verification requires owner dashboard access.
- External backup/restore attestation remains false in staging health.
- Local `.env` still carries the revoked token string (dead, 401) and should be cleaned by the owner.
