# DragonFly Beta Readiness Matrix

Status as of 2026-10-23. No merge or deployment occurred. Automated tests are mocked/local where noted; this is not a public-beta go decision.

| Workflow/capability | Classification | Evidence / caveat |
|---|---|---|
| Photo capture/import and review | Functional in code | Expo screen is present; no device/browser UI run in this sprint. |
| AI reconstruction | Functional, requires external configuration | Existing Replicate provider is preserved; no paid prediction run. Token/model/version, persistent storage, quotas and owner approval required. |
| Reconstruction job status/idempotency/restart | Functional, mocked tests | SQLite rows, bounded polling, recover by Idempotency-Key, fail interrupted jobs without automatic inference restart. Replicate operation ID is not persisted/resumed. |
| Editing, physical calibration, undo/redo/reset | Functional, automated backend coverage | Existing deterministic editor/calibration and units retained; model revisions/cursor persist. No real device/UI validation. |
| Accounts and session | Functional in code | Scrypt, expiry/revoke, server ownership, SecureStore native/sessionStorage web; helper tests pass. No device Keychain/Keystore or browser interactive test. |
| Project create/list/reopen/rename/delete | Functional in code | Authenticated endpoints, owner checks and integration coverage; user needs a durable disk for survival across Render redeploy. |
| GLB/STL export/download | Functional in code | Guest compatibility route; saved project downloads use bearer-authenticated artifact route. Backend mesh integrity tests pass; UI not browser/device tested. |
| Storage durability | Functional only when configured | SQLite and files use `EYE_DATA_DIR`; root Render has no persistent-disk configuration. Not ready until owner provisions a disk and stable secrets. |
| Backups | Functional local scripts; externally unconfigured | Backup/restore integrity round trip passes locally; no external destination, schedule or external restore drill. |
| CORS | Functional in code/config | Explicit origin allowlist; root Render names current frontend origin. Staging origin and deployed origin need owner verification. |
| Printability/slicer | Unavailable | `/v1/geometry/prepare-print` returns 501; draft heuristic is not slicer validation. |
| Printer discovery/order | Unavailable | Screen is gated; no partner/availability/ordering integration. |
| Sharing/community/likes | Unavailable | Legacy API is not deployed; visible entry points are gated or explicit unavailable states. |
| Billing/subscription/admin/invites | Unavailable/preview | Legacy JSON-backed API and routes are not deployed or production-integrated. |
| Native interactive 3D viewer | Unavailable | Existing viewer is web-only; use export/open action on native. Device behavior not tested. |
| Similar-design retrieval/license matches | Unavailable/preview | No fake result matches remain; legacy retrieval API is not deployed. |
| Landing page | Build verified; links require external configuration | `web-landing` builds. Store listings, universal-link association and legacy design/creator API setup remain owner tasks. |
| Dependency security | Needs remediation | `npm audit`: 20 findings (17 high, 3 moderate, 0 critical). More fixes require reviewed framework upgrade. |
| Public beta readiness | **Not ready** | Persistent disk/external backup, device/UI verification, audit remediation and legacy feature decisions remain. |
