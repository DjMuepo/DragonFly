# web-landing Build Repair Report

Date: 2026-10-22
Branch: `feature/application-completion`
Implementation commit: `19e08ad`

## Scope

Diagnose the `next: not found` build failure in `web-landing`, make it build, and review landing navigation to the main app. No production deployment, reconstruction pipeline, or `main` branch changes.

## Findings

- The failure was environmental: `node_modules` was absent and no lockfile existed. `npm install` provides `next`.
- Next 14.2.15's first build then auto-installed the latest `typescript@7.0.2`, `@types/react@19`, and `@types/node@26`, which are incompatible with Next 14 / React 18; the build crashed with `The "id" argument must be of type string`.
- Fix: pin `typescript@5.6.3`, `@types/react@18.3.12`, `@types/react-dom@18.3.1`, `@types/node@20.16.11`, add `package-lock.json`, and let Next write its standard `tsconfig.json`/`next-env.d.ts` updates.
- Upgraded `next` to `14.2.35` (same major, patch release). `npm audit` still reports 1 critical (`next`) and 1 high (`postcss`, via next); the only audit fix is `next@16`, a breaking upgrade that was not attempted.

## Navigation and Links

- App scheme `eyeplatform://` and `/design/<slug>` match `eye-expo/app.json` (`scheme: eyeplatform`) and route `eye-expo/app/design/[slug].tsx`. Slug is now URL-encoded.
- Home page had no links; added a "Get the App" link to `/get-app`.
- Store links defaulted to `#` (dead buttons). They now render only when `NEXT_PUBLIC_APPSTORE_URL` / `NEXT_PUBLIC_PLAYSTORE_URL` are set; otherwise "App store listings are not available yet."
- Not fixed (need owner input): `/creator/*` is listed in the universal-link association but the Expo app has no creator route; `public/.well-known` files contain placeholders (`ABCDE12345` team ID, `REPLACE_WITH_RELEASE_CERT_SHA256`); `NEXT_PUBLIC_API_BASE` defaults to `http://localhost:8000` and `NEXT_PUBLIC_SITE_ORIGIN` to `https://example.com`; design and creator pages call legacy `/v1/designs`/`/v1/creators` routes that root Render config does not deploy. `web-landing` is not part of root Render deployment.

## Changed Files

- `web-landing/package.json`, `web-landing/package-lock.json` (new)
- `web-landing/tsconfig.json`, `web-landing/next-env.d.ts` (Next-generated)
- `web-landing/.gitignore` (new: `.next/`, `node_modules/`)
- `web-landing/app/page.tsx`, `app/get-app/page.tsx`, `app/components/OpenAppButtons.tsx`

## Tests

- `npm install` — OK. `npm run build` — PASS (routes `/`, `/get-app`, `/design/[slug]`, `/creator/[creator]`, `/_not-found`).
- `npx tsc --noEmit` — PASS.
- `next start` smoke test: `/` 200 with `/get-app` link; `/get-app` 200 with no dead links.
- No lint/test scripts exist in `web-landing`. Dynamic design/creator pages were not exercised (no API available).

## Deployment

Not deployed; no production configuration changed; not merged.
