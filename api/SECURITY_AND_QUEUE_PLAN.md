# Security + Queue Plan

## Implemented in v46
- password hashing with PBKDF2
- password strength validation
- auth rate limiting for signup/login
- file-backed background job queue
- printer node online/queue status endpoints
- mobile tools for queue + printer nodes

## What this closes
- stronger auth foundation
- basic abuse resistance
- queue foundation for preview rendering, exports, and future training jobs
- operational visibility into printer node status

## Production next steps
- move auth tokens to secure signed tokens
- password reset / email verification
- Postgres-backed jobs
- real worker process / background executor
- secure secrets + env management
