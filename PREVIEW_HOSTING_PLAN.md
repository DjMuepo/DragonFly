# Preview Hosting Plan

## Implemented in v44
- preview generation now returns `preview_url`
- design publishing auto-generates preview assets
- local hosted preview copy endpoint:
  - `POST /v1/designs/{slug}/host-preview`

## Current behavior
1. design is published
2. preview image is generated
3. app can call host-preview endpoint
4. design page can use `preview_url`

## Production next steps
- replace local hosted copy with S3 / Cloudflare R2 upload
- CDN serve previews
- add signed upload or background job queue
- generate richer branded preview images from actual 3D renders
