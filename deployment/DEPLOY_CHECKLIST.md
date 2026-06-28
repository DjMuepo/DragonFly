# Beta Deployment Checklist

## API
- [ ] Set production env values
- [ ] Set `AUTH_TOKEN_SECRET`
- [ ] Set `DATABASE_URL`
- [ ] Set `PREVIEW_PUBLIC_BASE`
- [ ] Restrict CORS to production domains
- [ ] Run API container and verify `/health` and app routes

## Web landing
- [ ] Set real domain in env
- [ ] Set real App Store / Play Store links
- [ ] Deploy `.well-known` files
- [ ] Verify `/design/<slug>` routes
- [ ] Verify OpenGraph preview image URL

## Mobile
- [ ] Replace example domain in `app.json`
- [ ] Verify deep links
- [ ] Verify universal links
- [ ] Verify printer node tools
- [ ] Verify worker tool

## Operations
- [ ] Back up DB / persistent storage
- [ ] Add log capture
- [ ] Add uptime monitoring
- [ ] Add worker process supervision
