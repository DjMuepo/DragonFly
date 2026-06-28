# Beta Launch Plan

## Implemented in v48
- API Dockerfile
- production env templates
- compose example
- nginx reverse proxy example
- deployment checklist

## Purpose
This package closes the gap between a strong beta codebase and a repeatable beta deployment setup.

## Recommended deployment order
1. Deploy API
2. Deploy web landing
3. Configure domain + SSL
4. Verify `.well-known` files
5. Verify preview URLs
6. Verify mobile deep links
7. Run worker once
8. Smoke test publish/share/print flow

## Near-term production priorities
- replace example secrets/domains
- move to managed Postgres
- move previews to cloud object storage
- run worker as a supervised process
