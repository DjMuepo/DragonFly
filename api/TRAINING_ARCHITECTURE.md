# Training Architecture Foundation

## Implemented in v40
- Event store (`events_v2.jsonl`)
- Feature store (`feature_store.json`)
- Event ranking / importance scoring
- Nightly-style aggregation endpoint
- Family-specific learned defaults
- Draft adaptation endpoint

## Core idea
- Log everything cheaply
- Score events by value
- Aggregate in batches
- Update compact family feature profiles
- Adapt new drafts using learned defaults

## Family-specific signals captured
- min_thickness
- preferred_material
- reinforcement_bias
- fillet_bias
- failure_signals
- success_signals
- sample_weight

## New endpoints
- `POST /v1/training/event`
- `GET /v1/training/events`
- `POST /v1/training/aggregate`
- `GET /v1/training/features`
- `POST /v1/training/adapt`
