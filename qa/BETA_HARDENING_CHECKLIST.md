# Beta Hardening Checklist

## Security
- [ ] Replace placeholder secrets
- [ ] Rotate `AUTH_TOKEN_SECRET`
- [ ] Review rate limit thresholds
- [ ] Add secure token/session signing
- [ ] Add password reset flow
- [ ] Add email verification plan

## Data
- [ ] Decide SQLite vs managed Postgres for beta
- [ ] Back up persistent files
- [ ] Verify preview file retention
- [ ] Verify job queue persistence
- [ ] Verify design publish persistence
- [ ] Verify auth/session persistence

## Infra
- [ ] Set production domains
- [ ] Configure SSL
- [ ] Configure reverse proxy
- [ ] Configure `.well-known` routes
- [ ] Configure preview public base
- [ ] Set worker supervision

## App quality
- [ ] Validate all tool screens
- [ ] Validate publish/share path
- [ ] Validate printer path
- [ ] Validate community path
- [ ] Validate worker path
- [ ] Validate training insights path

## UX polish
- [ ] Review loading states
- [ ] Review error states
- [ ] Review empty states
- [ ] Review share copy
- [ ] Review landing page copy
- [ ] Review install CTA copy
