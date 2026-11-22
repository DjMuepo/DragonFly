# Real AI Reconstruction — Final Readiness Report

Date: 2026-11-22
Repository: DjMuepo/DragonFly
Branch: `feature/staging-deployment`
Implementation commit verified: `f27b098` (branch head; includes cancel-on-timeout safeguard `86cd824`). This task is verification-only — no code changes were made.
Prior reports: `2026-10-31-real-ai-reconstruction-preflight.md`, `2026-11-16-real-ai-reconstruction-preflight-update.md`, `2026-11-17-real-ai-preflight-token-rotation-followup.md`
Scope: final read-only readiness verification for exactly one controlled bottle-photo reconstruction on staging under the authorized USD 2.00 Replicate spend ceiling. No paid predictions were submitted. No Render settings were changed. No deployment, merge, or production change was made. No secret values were accessed or printed.

## Verdict

**READY, pending owner-side actions only.** All workspace-verifiable checks pass. The remaining steps (sections 4–5) require owner dashboard access or explicit owner authorization and cannot be completed from this workspace by design.

## 1. Read-only live checks — all PASS (2026-11-22)

- `GET https://dragonfly-staging-geometry-backend.onrender.com/health` → HTTP 200, version `0.4.0-alpha`, `environment=staging`, `provider=mock-test`, `mock_enabled=true`, storage ready/durable, SQLite integrity `ok`, migrations applied. **Paid inference is not reachable** on the running staging backend.
- `https://dragonfly-staging-frontend.onrender.com/` → HTTP 200.
- Replicate public versions page (https://replicate.com/tencent/hunyuan3d-2/versions): version `b1b9449a1277e10402781c5d41eb30c0a0683504fb23fab591ca9dfc2aabe1cb` remains **Latest and the only listed version** (author `@lucataco`, cog release `22.04`). This matches the configured `EYE_REPLICATE_MODEL_VERSION` candidate exactly.
- Replicate model page (https://replicate.com/tencent/hunyuan3d-2): pricing unchanged — approximately **USD 0.11 per run** (~9 runs per USD 1), Nvidia L40S, predictions "typically complete within 118 seconds", predict time varies with inputs. One typical run leaves wide headroom under USD 2.00; a worst-case 600 s run is ≈ USD 0.585 of active time plus cancellation lag.
- Unauthenticated `GET https://api.replicate.com/v1/models/tencent/hunyuan3d-2` → HTTP 401, confirming no credential leaked into these checks (status codes only; no token used or printed).
- Still outstanding in staging health: `external_backup_configured=false`, `restore_tested_attested=false` (unchanged; tracked risk, not a blocker for the single controlled test).

## 2. Static guardrail validation — PASS

- `deployment/render.staging.yaml` pins `EYE_RECONSTRUCTION_PROVIDER=mock-test`, `EYE_ENABLE_MOCK_PROVIDER="1"`, `EYE_ALLOW_PROCEDURAL_FALLBACK="0"`, `EYE_LOCAL_SEGMENTATION="0"`, and `autoDeploy: false` on both services; no Replicate secret in the blueprint. Re-validated directly and via `tests/staging_mock_test.py`.
- Local hygiene: the git-ignored backend `.env` still contains exactly one `REPLICATE_API_TOKEN` line (known-revoked — returned HTTP 401 on 2026-11-17) plus the `tencent/hunyuan3d-2` model-version value. Presence was checked by line count only; no value was read or printed. Owner should still blank the dead token to avoid confusion.

## 3. Local test results — all PASS, no paid calls (2026-11-22)

Backend (`eye-platform-alpha-geometry-backend/geometry-backend`, Python 3.12 `.venv312`):

| Suite | Command | Result |
| --- | --- | --- |
| Core integration | `PYTHONPATH=. .venv312/bin/python tests/core_integration_test.py` | PASS (exit 0) |
| Replicate timeout cancel | `PYTHONPATH=. .venv312/bin/python tests/replicate_timeout_cancel_test.py` | PASS (exit 0) |
| Reconstruction fidelity | `PYTHONPATH=. .venv312/bin/python tests/reconstruction_fidelity_test.py` | PASS — local invariants only; no inference (exit 0) |
| Staging mock provider + blueprint | `PYTHONPATH=. .venv312/bin/python tests/staging_mock_test.py` | PASS (exit 0) |
| CORS security | `PYTHONPATH=. .venv312/bin/python tests/cors_security_test.py` | PASS (exit 0) |
| Security stabilization | `PYTHONPATH=. .venv312/bin/python tests/security_stabilization_test.py` | PASS (exit 0) |

Frontend (`eye-expo`):

| Suite | Command | Result |
| --- | --- | --- |
| API failure recovery | `npm run test:api` | PASS (exit 0) |
| Model history | `npm run test:history` | PASS (exit 0) |
| Project mapping | `npm run test:projects` | PASS (exit 0) |
| Beta recovery integration | `npm run test:stabilization` | PASS (exit 0) |

Skipped/blocked checks (unchanged rationale):

- `pytest` is not installed in `.venv312`; the three "unittest-style" backend suites are script-style modules with module-level assertions, so `python -m unittest tests.<m>` reports "Ran 0 tests" (exit 5) while still executing the checks at import. They were therefore run with their native script runner (`PYTHONPATH=. python tests/<m>.py`), each exiting 0 after printing PASS.
- Render dashboard verification (rotated token presence, disk, live quota values): blocked — no Render credential in this workspace; owner-side only.
- Account-level Replicate availability with the rotated token: blocked by design — the rotated token lives only in Render and must never enter this workspace.
- No paid prediction was created; the cancel-on-timeout path (`86cd824`) remains validated against mocked transport only.

## 4. Owner-side prerequisites before the single paid test (unchanged)

1. Replicate billing (https://replicate.com/account/billing): confirm prepaid balance, keep auto reload **OFF**; set any legacy spend limit low. A zero-balance prepaid cutoff is the strongest available ceiling; Replicate documents a rare overrun case, so USD 2.00 is approximated, not provably guaranteed.
2. Free token check (owner-side, outside this repo): `GET /v1/models/tencent/hunyuan3d-2/versions/b1b9449a…` with the rotated token → expect HTTP 200.
3. Render dashboard: confirm `REPLICATE_API_TOKEN` exists on `dragonfly-staging-geometry-backend` only; confirm disk mount, `EYE_DATA_DIR`, signing secret, `PUBLIC_BASE_URL`, `EYE_ALLOWED_ORIGINS`, and live quotas (1/day per user and guest, 1 active job each).
4. Redeploy staging backend from a commit including `86cd824` (the running staging backend predates it) — **owner authorization required**.
5. For the test window only: `EYE_RECONSTRUCTION_PROVIDER=replicate`, `EYE_REPLICATE_MODEL_VERSION=tencent/hunyuan3d-2:b1b9449a1277e10402781c5d41eb30c0a0683504fb23fab591ca9dfc2aabe1cb`, `EYE_ENABLE_MOCK_PROVIDER=0`; keep `EYE_ALLOW_PROCEDURAL_FALLBACK=0` and all quotas.

## 5. Test procedure (owner-gated; unchanged)

One original bottle photo with recorded checksum; one signed-in workflow; one Idempotency-Key; exactly one logical job; recover (never resubmit) on transport loss; watch the Replicate dashboard during the run; verify the prediction reaches a terminal state and reconcile actual billed cost against USD 2.00; immediately return staging to guarded mock mode and confirm `/health` shows `provider=mock-test`, `mock_enabled=true`.

## Changed files

- `docs/codex-reports/2026-11-22-real-ai-reconstruction-final-readiness.md` (this report; committed separately).

No source, configuration, or deployment files were modified.

## Deployment status

Unchanged. Staging remains in guarded mock mode (verified live). Production untouched. No merge performed. This report authorizes nothing; the single paid test requires explicit owner approval after the owner-side verifications above.

## Remaining issues

- Provable hard USD 2.00 cap remains impossible on Replicate's current billing model (prepaid zero-balance cutoff with documented rare overrun is the best mechanism).
- Render-side secret/disk/quota verification requires owner dashboard access.
- External backup/restore attestation remains false in staging health.
- The running staging backend predates `86cd824` and must be redeployed (owner-authorized) before the paid test to carry the cancel-on-timeout safeguard.
- Local git-ignored `.env` still carries the revoked token string (dead; cleanup is owner hygiene, not a spend risk).
