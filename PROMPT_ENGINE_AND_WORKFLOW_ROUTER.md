# Prompt Engine + Workflow Router

## Implemented in v53
- prompt engine service
- live detection routing service
- `/v1/vision/live-detect` endpoint
- mobile prompt engine prototype screen

## Purpose
Turn lightweight live recognition into actionable flows such as:
- Scan the World
- Fix This Object
- Instant Builder
- Premium upsell for paid Scan the World

## Core behavior
- prompt only on supported families
- require stable detections across several frames
- debounce repeated prompts
- gate premium Scan the World prompts for paid accounts
