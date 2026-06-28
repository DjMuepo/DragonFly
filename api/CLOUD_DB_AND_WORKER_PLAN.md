# Cloud DB + Worker Foundation

## Implemented in v47
- Postgres adapter scaffold
- Postgres health endpoint
- worker executor foundation
- one-shot worker run endpoint
- mobile worker tool screen
- env example for DB + preview config

## New endpoints
- `GET /v1/db/postgres-health`
- `POST /v1/jobs/run-once`

## What this unlocks
- future move from local/file-backed systems to managed Postgres
- running preview/export/training jobs through a worker path
- easier path to production background execution
