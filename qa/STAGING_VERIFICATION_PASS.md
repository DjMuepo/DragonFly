# Staging Verification Pass

## Goal
Run a final go/no-go verification against the deployed staging environment before inviting closed beta users.

## Required staging URLs
- Web: `https://staging.example.com`
- API: `https://api.staging.example.com`

## Verify config first
1. API `/health`
2. API `/v1/db/postgres-health`
3. Hosted design page route works
4. `.well-known` files are reachable
5. Preview URLs resolve
6. Deep links and universal links are wired to staging domain

## Required user journeys
### A. New user journey
- Sign up
- Log in
- Open community
- Open design
- Like design
- Open creator page

### B. Creator journey
- Capture/build object
- Open draft
- Apply learned defaults
- Open print screen
- Generate STL
- Publish design
- Confirm share URL
- Confirm preview URL
- Open hosted design page

### C. Print routing journey
- Nearby printers load
- Online nodes rank higher than offline nodes
- Submit print request
- ETA/status returned

### D. Ops journey
- Enqueue preview job
- Run worker once
- Confirm processed count increments
- Confirm preview job ends in done state

## Launch gate
Closed beta can proceed only if:
- no blocker issues
- no broken publish/share path
- no broken auth path
- no broken landing page path
- no broken worker path
