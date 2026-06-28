# Camera Router Integration

## Implemented in v55
- camera router service
- `/v1/camera/route` endpoint
- mobile camera router prototype
- direct routing from live detections into:
  - Scan the World
  - Fix This Object
  - Instant Builder

## Purpose
Make live camera detections feel automatic and useful by sending actionable objects into the correct workflow.

## Examples
- chair → Scan the World
- bracket → Fix This Object
- container → Instant Builder
- unsupported/low confidence → no action

## Next steps
- connect camera frames directly into the router
- feed router result into app navigation automatically
- attach Object DNA creation at route accept time
- add collaborative scan routing
