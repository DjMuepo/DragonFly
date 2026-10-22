# DragonFly Remaining Beta Blockers (after core integration)

Not merge-ready for public beta until the owner resolves the items below. Nothing was deployed.

## Blocking, requires owner decision or infrastructure

1. **Durable storage is not provisioned.** Render needs a persistent disk (plan and `render.yaml` change), `EYE_DATA_DIR`, `EYE_STORAGE_DURABLE=1`, a stable `EYE_SIGNING_SECRET`, and a backup routine. Until then accounts, projects and model files are lost on redeploy. See `DRAGONFLY_PERSISTENCE_DESIGN.md`.
2. **Single instance only.** SQLite plus local files cannot run on multiple instances. Scaling requires a Postgres `Repository` implementation and object storage.
3. **No end-to-end test in a real browser or device.** Backend flows are tested over the ASGI test client and a live HTTP smoke test only. The Expo UI was type-checked and built, not exercised. No iPhone, Mobile Safari or Android run was done. Native builds have no persisted session (the store only uses `localStorage` on web) and the native viewer remains web-only.
4. **No real reconstruction was run.** All reconstruction tests use a mock provider. Replicate behavior with owned projects (source photo retention, long jobs, process restart during a paid prediction) is unverified against the real service. By design a restarted job is failed, not resumed, so a user may lose a paid prediction and must retry.
5. **Legacy `api/` features remain non-operational:** sharing and public design pages, printer discovery and orders, subscriptions and entitlements, admin and invites, challenges, learning/training, world map. The frontend still renders screens that call them and they fail against the deployed service. They need either deployment with real storage and auth or removal from navigation.
6. **`web-landing` links to the app are placeholders:** store URLs, deep-link association files and design/creator pages depend on the legacy API.

## Security and operations gaps

7. No password reset, email verification, account deletion or session listing. Password-reset email needs a mail provider.
8. Login throttling is per process and per email only. No IP limit, CAPTCHA or shared limiter.
9. The session token is stored in browser `localStorage` on web (readable by any script on the origin). A cookie-based session or hardened CSP is a separate decision.
10. CORS is `*`. Restrict to the frontend origin before beta.
11. Guest (unsaved) models are still downloadable by filename without authentication, as before. Retention and cleanup of unsaved files do not exist.
12. Signed file links last 15 minutes; a screen left open longer must reload the project. Links are bearer capabilities.
13. Original photos are now stored for signed-in users. A privacy notice, retention policy and consent copy are required before beta.
14. Deleting a project deletes files and rows immediately with no undo or trash.
15. No audit log, no rate limits on generation per user (paid inference exposure), no quotas.

## Functional limits

16. A project holds one object lineage; there is no duplicate/fork, import or multi-user sharing.
17. Guest-to-project saving requires every local revision to carry a job id; models created before this branch cannot be saved and must be regenerated.
18. Editing capabilities are unchanged and finite; print readiness is still unavailable (HTTP 501).
19. Reconstruction fidelity across real objects is still unqualified (see the evaluation work).
20. The `ProjectPanel` cursor sync is best-effort: if the network drops during undo, the server position lags until the next change and the panel shows a warning.
