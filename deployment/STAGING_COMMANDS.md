# Staging Commands

## API health
curl https://api.staging.example.com/health

## Postgres config health
curl https://api.staging.example.com/v1/db/postgres-health

## List jobs
curl https://api.staging.example.com/v1/jobs

## Run worker once
curl -X POST https://api.staging.example.com/v1/jobs/run-once \
  -H "content-type: application/json" \
  -d '{"limit":25}'

## List printer nodes
curl https://api.staging.example.com/v1/printers/nodes
