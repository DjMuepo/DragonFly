# Real AI Reconstruction Preflight

Date: 2026-10-31
Repository: DjMuepo/DragonFly
Branch: `feature/staging-deployment`
Inspected implementation commit: `e91ef296af3e221e4654d882674d7dab3f23ac24`
Scope: read-only preparation of exactly one bottle-photo reconstruction, with a maximum authorized total Replicate inference spend of USD 2.00. Submission requires owner review of this preflight. This report does not authorize execution.

## Decision: No-Go

No paid prediction was submitted. Mock mode remains enabled. No staging configuration, credentials, infrastructure, production deployment or branch merge was changed. The exact deployed Replicate version, Render secret configuration and an enforceable USD 2.00 spending ceiling could not be verified.

## Model and version

The ignored local environment file specifies this candidate:

`tencent/hunyuan3d-2:b1b9449a1277e10402781c5d41eb30c0a0683504fb23fab591ca9dfc2aabe1cb`

This is a local configuration observation, not verification of the deployed staging environment. Live staging currently selects `mock-test`, not Replicate. The public version-specific page returned HTTP 404 and the unauthenticated version API returned HTTP 401. Neither establishes whether the candidate is available to the owner's account. Do not substitute another version silently.

## Pricing and cost estimate

The official public model page, https://replicate.com/tencent/hunyuan3d-2, was read during the October 31 preflight. It displayed:

- USD 0.000975 per second.
- USD 0.12 median (`p50price`) run cost, also described as approximately eight runs per USD 1, varying by inputs.

Expected cost for planning: approximately USD 0.12 per reconstruction, based on the published median, not a quote for this bottle photo or exact candidate version.

At the observed rate, exactly 600 billable seconds would cost USD 0.585. This is a conditional estimate, NOT a maximum charge. Exact-version pricing, all billable runtime behavior and any account-specific terms were not verified. Recheck official pricing immediately before any approved submission.

## Observed staging configuration

- Backend: `https://dragonfly-staging-geometry-backend.onrender.com`.
- Frontend: `https://dragonfly-staging-frontend.onrender.com`.
- Backend `/health` returned HTTP 200, `environment=staging`, `provider=mock-test`, `mock_enabled=true`, storage ready and SQLite integrity `ok`.
- Health reported `storage.durable=true`; this is the application's configured attestation, not independent confirmation of the Render disk mount.
- The deployed frontend bundle contained the staging backend URL.
- External backup configuration and restore-test attestation were false.
- No Render API credential was available to inspect dashboard environment settings. Secure configuration of `REPLICATE_API_TOKEN` in Render remains unverified. A local token's existence is not evidence that Render holds the correct secret.

## Budget safeguards and limitations

- Authorization covers at most USD 2.00 total and starts with exactly ONE reconstruction, not unlimited testing.
- Existing daily quotas, active-job caps, CORS, authentication, ownership and upload protections must remain enabled.
- The current client retries a transport-interrupted POST once using the same Idempotency-Key. This aims to replay the durable job, not start another prediction. Confirm deployed behavior before execution; do not use the multi-step mock smoke runner as a real-inference runner.
- Unknown provider outcomes and interrupted backend jobs must not be retried automatically. Do not accept the UI's new-attempt confirmation as authorization for another prediction within this test.
- The backend's default 600-second prediction polling deadline stops waiting; it does not cancel or guarantee termination of the remote prediction. The default 60-second HTTP timeout also does not establish an inference spending limit.
- Database idempotency and quotas prevent some duplicate submissions but do not impose a dollar cap. Provider prediction IDs are not durably tracked for reconciliation after a backend restart.
- Therefore, the USD 2.00 ceiling cannot currently be enforced by DragonFly. Monitoring, a timeout or an approximate median price is insufficient proof of a hard ceiling. Do not submit until the owner can verify an applicable provider-side spending bound or another demonstrably enforceable total-cost control.

## Required changes before a reviewed controlled test

1. Rotate/revoke the exposed local Replicate token. A prior diagnostic accidentally emitted its value in terminal output. The value is intentionally absent from this report; it was not committed or used for inference. Treat it as exposed.
2. In the Render dashboard, verify the isolated staging backend service identity and actual disk mount, correct `EYE_DATA_DIR`, `EYE_STORAGE_DURABLE=1`, `EYE_REQUIRE_DURABLE_STORAGE=1`, stable `EYE_SIGNING_SECRET`, staging `PUBLIC_BASE_URL`, and exact staging frontend `EYE_ALLOWED_ORIGINS`. Do not change production services or secrets.
3. Verify the candidate model/version is available and its exact pricing. Verify that a single request cannot exceed the remaining USD 2.00 authorization, including uncertain outcomes. If this cannot be proven, remain No-Go.
4. Verify a rotated token is configured through Render's secret/environment manager. Never print it, include it in a URL, or commit it. Check secret presence without retrieving its value into reports.
5. Prepare a clear, original bottle photo (not a UI screenshot), confirm permission to use it, and retain its checksum for input/output comparison. No bottle photo was uploaded or submitted during this preflight.
6. After owner review and only when ready for the single test, manually switch ONLY staging to `EYE_RECONSTRUCTION_PROVIDER=replicate`, the exact verified `EYE_REPLICATE_MODEL_VERSION`, and `EYE_ENABLE_MOCK_PROVIDER=0`. Preserve quotas and fallback-disabled behavior. This report does not execute that configuration change or deploy it.
7. Confirm deployed health/provider and frontend backend URL again. Use the existing signed-in capture/review/reconstruction workflow with one unique cryptographic Idempotency-Key and exactly one logical job. If a POST response is lost, inspect/recover the same job; do not create a new key or click another AI attempt.
8. Capture job/provider identifiers, terminal outcome, actual billed cost, original-photo reference and model artifacts. If outcome or cost is uncertain, stop and reconcile in Replicate before any further action. Return staging to guarded mock mode after the reviewed test using an owner-approved configuration procedure.

## Blockers

- Exact deployed candidate model/version and exact-version pricing are not verified.
- Render token presence/security and actual persistent disk mount cannot be independently inspected with current access.
- A hard USD 2.00 total ceiling is not enforced by existing application timeouts, quotas or idempotency.
- The exposed local token requires rotation before use.
- External backups/restore drill are not attested; no actual device/browser paid-inference flow was tested.

## Checks and results

- Git status: current branch based on the inspected implementation commit; no tracked modifications at preflight-report save time.
- Staging backend health: HTTP 200, guarded mock provider enabled; no generation endpoint called.
- Staging frontend: HTTP 200 and compiled staging backend reference found.
- Official Replicate model page: pricing observed as above. Candidate version public page: HTTP 404; unauthenticated candidate version API: HTTP 401.
- Local environment: git-ignored. Render API credential: unavailable; no secret-store validation performed.
- Tests/builds: not rerun for this documentation-only save. Previous staging-preparation test results are recorded in the separate implementation report; they do not verify real inference pricing or budget enforcement.

Report publication is documentation-only. No inference, merge, deployment or infrastructure provisioning occurred. The report commit is separate from the inspected implementation commit.