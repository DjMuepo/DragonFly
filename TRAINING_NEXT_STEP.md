# Training Integration Next Step

## Implemented in v41
- Learned defaults are now wired into the main reconstruction flow
- New endpoint:
  - `POST /v1/vision/apply_learned_defaults`
- New mobile screen:
  - `/training/insights`

## Result
Newly reconstructed drafts can automatically benefit from:
- learned minimum thickness
- preferred material
- reinforcement bias
- fillet bias

## Next logical step
- scheduled aggregation jobs
- preview asset generation from published designs
- universal link deployment
