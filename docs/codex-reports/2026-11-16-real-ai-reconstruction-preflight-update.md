# Real AI Reconstruction Preflight — Update

Date: 2026-11-16
Repository: DjMuepo/DragonFly
Branch: `feature/staging-deployment`
Inspected implementation commit: `22f3d0e` (no application code was changed by this task; this update is documentation-only)
Prior report: `2026-10-31-real-ai-reconstruction-preflight.md`
Scope: continue the read-only preflight for exactly one bottle-photo reconstruction under a maximum authorized total Replicate spend of USD 2.00. No paid inference was run. No Render settings, deployments, merges, or production services were touched.

## Decision: No-Go for autonomous submission; owner-gated Go is close

Several October blockers are now resolved or materially narrowed. The remaining blockers require owner access to the Render dashboard and the Replicate billing page; they cannot be closed from the repository.

## Model and version — VERIFIED (public listing)

- Candidate: `tencent/hunyuan3d-2:b1b9449a1277e10402781c5d41eb30c0a0683504fb23fab591ca9dfc2aabe1cb`
- The public versions page (https://replicate.com/tencent/hunyuan3d-2/versions) now lists version `b1b9449a…` as **Latest**, and it is the only listed version. Author: `@lucataco`, published roughly 1 year 9 months ago. The version-specific public page, which returned HTTP 404 during the October preflight, now resolves.
- Unresolved: whether the owner's Replicate account can run this version was NOT verified, because no valid API token is available locally (see Token status). Account-level availability must be confirmed with the rotated token before submission.
- The backend accepts `owner/model:version` references and extracts the version hash for `/v1/predictions` (`ReplicateGPUProvider._prediction_request`), so the candidate string above is the correct `EYE_REPLICATE_MODEL_VERSION` format.

## Pricing — observed 2026-11-16

From the official public model page (https://replicate.com/tencent/hunyuan3d-2) and pricing page (https://replicate.com/pricing):

- Model page estimate: approximately **USD 0.11 per run**, or about 9 runs per USD 1 (October: USD 0.12 / 8 runs per USD 1).
- Hardware: Nvidia L40S at **USD 0.000975 per second** (USD 3.51/hour) — unchanged since October.
- Typical completion: ~118 seconds → ≈ USD 0.115 at the L40S rate. Predict time "varies significantly based on the inputs."
- Conditional worst-case at the backend's default 600-second polling deadline: 600 s × 0.000975 = **USD 0.585**. This is NOT a maximum charge: the backend deadline stops waiting but does not cancel the remote prediction, so billing can continue until the prediction terminates on Replicate's side. Setup and idle time on public models are free; only active time is billed.
- One run at typical cost leaves ample headroom inside the USD 2.00 authorization, but a hard per-run ceiling is still not provable from pricing alone.

## Spending controls — key finding

- Replicate **deprecated the "set a monthly spend limit" feature for new customers on 2025-07-01** (changelog: https://replicate.com/changelog/2025-07-01-set-a-monthly-spend-limit). Legacy accounts may still have it at https://replicate.com/account#limits.
- The enforceable mechanism for most accounts is now **prepaid credit** (https://replicate.com/docs/topics/billing/prepaid-credit): usage deducts from a purchased balance, and "as soon as your balance hits zero, we will prevent any new work from starting and shut down any infrastructure." Caveat: "In rare cases, a prediction may run over your credit balance," with the overrun charged to the default payment method.
- **Auto reload must remain disabled** for the balance to act as a cap (minimum reload settings are $5 threshold / $15 balance, which would exceed the $2 authorization if triggered).
- Practical ceiling for this test: the owner should confirm on https://replicate.com/account/billing whether the account is prepaid or billed in arrears, confirm the current balance/limit, and keep auto reload off. A low prepaid balance approximates — but does not perfectly guarantee — the USD 2.00 ceiling due to the documented overrun case.
- Application-side bound: the staging blueprint (`deployment/render.staging.yaml`) sets `EYE_DAILY_RECONSTRUCTION_QUOTA_PER_USER=1`, `EYE_DAILY_RECONSTRUCTION_QUOTA_PER_GUEST=1`, and max 1 active job each. If these values are also live in Render, worst-case paid submissions are bounded at ~2/day even on operator error. Live values were not independently verified.

## Token status — rotation confirmed effective; local copy is dead

- The owner reports the staging backend's `REPLICATE_API_TOKEN` was replaced in Render.
- Free, read-only API checks from this workspace using the token still present in the git-ignored local `.env` returned **HTTP 401** for both `/v1/account` and the model-version endpoint. The previously exposed local token is therefore revoked and unusable — the required rotation (October blocker 1) is confirmed effective from this side.
- No token value was printed, logged, committed, or placed in a URL during these checks.
- Consequences: (a) the stale token should be removed from or replaced in the local `.env` before any local real-inference testing; (b) presence and validity of the NEW token in Render cannot be verified from this workspace — the owner must confirm it in the Render dashboard (secret presence only, never the value).

## Live staging observations (read-only, 2026-11-16)

- Backend `https://dragonfly-staging-geometry-backend.onrender.com/health`: HTTP 200, version `0.4.0-alpha`, `environment=staging`, `provider=mock-test`, `mock_enabled=true`, storage ready/durable attested, SQLite integrity `ok`, migrations applied.
- Still outstanding: `external_backup_configured=false`, `restore_tested_attested=false` ("No external backup destination is configured").
- Frontend `https://dragonfly-staging-frontend.onrender.com/`: HTTP 200. The compiled entry bundle contains 3 references to the staging backend URL and **zero** references to the production backend (`eye-geometry-backend.onrender.com`). Frontend/backend pairing is correct.
- All previously completed staging functionality (capture, mock reconstruction, editing, undo/redo, saved projects, reopen, GLB/STL export — iPhone-verified by the owner) is untouched; no configuration was changed.

## Free/local validation tests — all PASS, no paid calls

Backend (`eye-platform-alpha-geometry-backend/geometry-backend`, Python 3.12.3 via `.venv312`):

- `PYTHONPATH=. .venv312/bin/python tests/core_integration_test.py` — PASS (auth, projects, durable jobs, artifacts, restart-recovery phase; inference mocked). Note: this suite must be run directly as a script, not via `unittest` module discovery.
- `.venv312/bin/python -m unittest tests.staging_mock_test` — "staging mock provider PASS" (also statically validates `deployment/render.staging.yaml`: isolated service names, `autoDeploy: false` ×2, no Replicate secret in the mock blueprint).
- `.venv312/bin/python -m unittest tests.cors_security_test` — "CORS security PASS".
- `.venv312/bin/python -m unittest tests.security_stabilization_test` — "security stabilization PASS".

Frontend (`eye-expo`, Node):

- `npm run test:api` — "API failure recovery PASS".
- `npm run test:history` — "model history PASS".
- `npm run test:projects` — "project mapping PASS".
- `npm run test:stabilization` — "beta recovery integration PASS".

Skipped/blocked checks:

- `pytest` is not installed in `.venv312`; suites were run with their native runners as documented in each file.
- No Render API credential: Render dashboard environment/secret/disk verification remains blocked from this workspace.
- No paid Replicate prediction was created; account-level model availability check is blocked until a valid token is used (owner-side).

## Remaining requirements before the single reviewed test (owner actions)

1. In Replicate billing (https://replicate.com/account/billing): confirm prepaid vs. invoiced, confirm balance, disable auto reload. If a legacy spend limit exists at https://replicate.com/account#limits, set it low.
2. With the rotated token (owner-side, never in this repo): one free read-only `GET /v1/models/tencent/hunyuan3d-2/versions/b1b9449a…` to confirm HTTP 200 account availability of the exact version.
3. In the Render dashboard: confirm the new `REPLICATE_API_TOKEN` is present on `dragonfly-staging-geometry-backend` only; confirm disk mount, `EYE_DATA_DIR`, durable flags, signing secret, `PUBLIC_BASE_URL`, `EYE_ALLOWED_ORIGINS`, and that the live quota values match the blueprint (1/day).
4. Re-verify current model-page pricing immediately before submission.
5. For the test window only, switch staging (never production) to `EYE_RECONSTRUCTION_PROVIDER=replicate`, `EYE_REPLICATE_MODEL_VERSION=tencent/hunyuan3d-2:b1b9449a1277e10402781c5d41eb30c0a0683504fb23fab591ca9dfc2aabe1cb`, `EYE_ENABLE_MOCK_PROVIDER=0`; keep `EYE_ALLOW_PROCEDURAL_FALLBACK=0` and all quotas.
6. Use one original bottle photo with a recorded checksum, one signed-in workflow run, one Idempotency-Key, exactly one logical job; on transport loss, recover the same job — never a new attempt.
7. Capture prediction ID, terminal status, and actual billed cost from the Replicate dashboard; reconcile before any further action; then return staging to guarded mock mode.

## Remaining blockers

- Render-side secret/disk/quota verification requires owner dashboard access.
- A provable hard USD 2.00 ceiling still depends on the account's billing mode (prepaid balance with auto reload off is the available mechanism; monthly spend limits are deprecated for new accounts).
- External backup/restore attestation remains false in staging health.
- Local `.env` still contains the revoked token string and should be cleaned before local real-inference use.

## Checks and results summary

- Git: branch `feature/staging-deployment` at `22f3d0e`; no tracked modifications other than this report and a pointer line in the prior report.
- Staging backend health: HTTP 200, guarded mock mode. Staging frontend: HTTP 200, correct backend pairing.
- Replicate: version publicly listed (Latest); pricing ~$0.11/run, L40S $0.000975/s; spend-limit deprecation and prepaid-credit cutoff behavior documented; local token confirmed revoked (401).
- Local tests: 4 backend suites PASS, 4 frontend suites PASS. No paid inference, no deployment, no merge, no production change.

Deployment status: unchanged — staging remains in guarded mock mode; production untouched. This report authorizes nothing; execution of the single paid test requires explicit owner approval after the owner-side verifications above.
