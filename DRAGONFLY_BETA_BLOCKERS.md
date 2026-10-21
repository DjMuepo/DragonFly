# DragonFly Public Beta Blockers

Audit date: 2026-10-21. Source baseline: production `main` `2ac30ecb6e69dc06bb55d90556322474c87ea569`. This list separates safe code fixes in the feature branch from dependencies requiring service owners or real-world evidence.

## P0 — Core flow / truthful status

1. **Production API routing is split.** Root `render.yaml` deploys the geometry backend and static Expo frontend. The account, saved-design, legacy parametric STL, sharing, printer, feature-admin and many workflow endpoints live under the separate `api/` app, which root Render config does not deploy. Setting frontend API base to the geometry backend makes those routes unavailable. No service was added or deployed here.
2. **Local failure recovery is incomplete.** Geometry `JOBS` and model artifacts are process-local/filesystem. A Render restart can lose job status and output; durable storage/job recovery is required before claiming robust public beta.
3. **Single-image visual fidelity is not qualified.** A prior “transparent cup” artifact was inspected from a saved output whose supplied input was a UI screenshot, not the original camera photograph. No valid controlled real-photo reconstruction matrix exists. Watertight output is not a fidelity pass; no inference was run in this sprint.
4. **3D viewer support is web-only.** `eye-expo/app/snap/viewer.tsx` loads model-viewer only on `Platform.OS === 'web'`; native branch explicitly says interactive viewing is web-only. Actual iPhone Safari and supported native-device tests remain required.
5. **Print readiness must not be called complete.** Reconstructed-mesh minimum feature thickness is `not_measured`; slicer integration is absent. Active geometry `/prepare-print` now truthfully returns HTTP 501. Legacy parametric printability is heuristic only.

## P1 — Identity, projects, data durability

1. **Account backend not connected in deployed topology.** Account screen calls `/v1/auth/signup`, `/login`, `/my-designs`, but those routes exist in the separate legacy API, not active geometry service.
2. **Legacy auth/storage is not production-hardened.** JSON-file users/sessions/rate limits have no proven atomic multiworker behavior, database backup/migration, token expiry/revocation, CSRF/session transport policy, or owner-level deployment path. Snap Zustand persists only a subset in web localStorage; native restart persistence is not implemented.
3. **Sharing uses demo/bootstrap data.** Legacy JSON store seeds sample designs, preview service can produce placeholder/example outputs, and ownership/auth checks are incomplete. Public sharing must be wired to durable, authenticated storage before claiming user-owned saved projects.

## P2 — Advanced product functions

1. **Printer discovery is seeded sample data.** This sprint disables order submission claims. Live partner catalog, availability verification, order idempotency, payment, printer-side acceptance, status tracking, cancellation, disputes and refunds are not implemented.
2. **Billing/feature entitlements are not integrated.** Client-provided `is_paid` or `user_tier` cannot be an authority. No payment processor or server-verified entitlement exists; gates now fail closed where explicitly used.
3. **Advanced geometry is limited.** Deterministic feature edits support a finite parser/Boolean set; fillets/chamfers/threads/freeform/semantic removal are explicitly unsupported. Topology validity does not certify manufacturability.
4. **Navigation contains legacy/demo surfaces.** Some `/snap/*` and legacy API routes are separate from the one-photo geometry path; test each advertised route against active deployment before beta exposure.

## Release Gates Before Public Beta

- Select and deploy the intended API route topology; preserve current production endpoints and recovery rollback.
- Run full mobile/iPhone capture-to-GLB-to-edit/calibrate/undo/export on actual devices and persistent model URLs; include denied camera/location/network and process-restart paths.
- Resolve native 3D viewer support or explicitly scope public beta to tested mobile Safari/web.
- Connect authenticated durable accounts/projects or disable those claims; verify ownership/isolation, migrations, backups and deletion.
- Replace sample printer/payments with real contracts or hide order language; never report a submitted order absent partner acknowledgement.
- Validate reconstructed mesh fidelity with consented real photos across categories; retain failures and human reviews.
- Integrate a real slicer or label existing heuristics as estimates; do not claim wall thickness checks.
- Review session/token storage, public route authorization, rate limiting, CORS, file access, signed download URLs and user-private diagnostics.
- Perform independent dependency/model-weight/data-license and privacy review; retain notices and commercial/geographic approvals.
- Resolve legacy `web-landing` build setup separately if that app is required. It currently has no installed `next` binary in this environment.

No merge, deployment, paid inference or infrastructure change was performed in this task.
