# Eye Platform API (MVP)

This is a lightweight FastAPI backend that supports the Expo mobile MVP.

## Run locally

```bash
cd api
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health check:

- GET http://localhost:8000/health

## Mobile configuration

When running on a physical phone, set your LAN IP (not localhost):

```bash
EXPO_PUBLIC_API_BASE=http://YOUR_LAN_IP:8000 npm run start
```

## Endpoints

- POST `/v1/jobs` → creates a job and returns PUT URLs
- PUT `/v1/uploads/{job_id}/hero` → upload hero image bytes
- PUT `/v1/uploads/{job_id}/burst/{index}` → optional burst frame upload
- GET `/v1/jobs/{job_id}` → poll job status + results

> Note: This MVP backend returns mocked retrieval results and a dummy STL download.


## Build the local open-model index (MVP)

```bash
python tools/library_ingest.py --input sample_library/models.json
```

This creates/updates `api/data/library.db` and enables `/v1/library/search` to return real results (license-aware).

## Remote metadata ingestion (compliant mode)

This project supports indexing *metadata-only* from multiple sources. Files are NOT downloaded/rehosted unless you explicitly add a connector that is permitted to do so.

Examples:

```bash
python tools/ingest_remote.py --source thingiverse --query hook --limit 50
python tools/ingest_remote.py --source nih3d --query adapter --limit 50
python tools/ingest_remote.py --source grabcad --query bracket --limit 50 --allow-restricted
```

List sources:
```bash
curl http://localhost:8000/v1/sources
```

## NIH 3D Print Exchange (metadata ingestion)

Ingest NIH entries by ID (metadata + deep link, license-aware):

```bash
python tools/ingest_nih_by_ids.py --ids 3DPX-021858 3DPX-021857
```

Restricted licenses are skipped unless you pass:
```bash
python tools/ingest_nih_by_ids.py --ids 3DPX-021858 --allow-restricted
```

## Telemetry / Learning events (local)

The API logs anonymous events to a local SQLite DB (default: api/data/events.db).

- Log endpoint: `POST /v1/events/log`
- Export endpoint: `GET /v1/events/export?limit=1000`

Export to JSONL for training:
```bash
python tools/export_events_jsonl.py --out events.jsonl --limit 50000
```

## Build a structural learning dataset

After exporting events to JSONL:

```bash
python tools/build_structural_dataset.py --in events.jsonl --out structural_dataset.jsonl
```

Each line is a supervised example mapping `before params` -> `strengthen action` with `delta` improvement.

## Print outcome + usefulness labels

The mobile app logs:
- `useful_yes` / `useful_no`
- `print_outcome_success` / `print_outcome_fail`
- `print_feedback` with failure type + notes

These are merged into `structural_dataset.jsonl` by session when you run:
```bash
python tools/build_structural_dataset.py --in events.jsonl --out structural_dataset.jsonl
```

- `review_submit` with rating + graded dimensions (fit/strength/finish/ease) and optional photo flag

## Neural policy (PyTorch)

The API can auto-train a small neural policy from `events.jsonl` on startup (when >=10 strengthen examples exist).
It saves:
- latest: `app/models/structural_policy.pt`
- versioned: `app/models/structural_policy_YYYYmmddHHMMSS.pt`

Manual training:
```bash
cd api
python tools/export_events_jsonl.py --out events.jsonl --limit 50000
python tools/train_policy_nn.py --events events.jsonl --epochs 15
```

## FAISS vector index (server-side)

This project now supports FAISS for model retrieval.

Build manually:
```bash
cd api
python tools/build_faiss_index.py
```

FAISS files are stored under:
- `api/data/faiss/models.index`
- `api/data/faiss/models_meta.json`

The app stays lightweight because the vector index is kept on the server, not on the user's device.

## Vision core (single-photo-first scaffolding)

New endpoints:
- `POST /v1/vision/classify` → object family + confidence
- `POST /v1/vision/segment` → basic fallback mask + masked preview files
- `POST /v1/vision/retrieve` → image-based retrieval against FAISS/index
- `GET /v1/vision/retrieve_text?q=...`
- `POST /v1/vision/draft` → single-view draft metadata (silhouette + depth prior)

These are the first production scaffolds for the photo → object understanding → editable draft pipeline.

## Wired mobile vision flow

The Expo Snap flow now calls:
- `/v1/vision/segment` from Cutout
- `/v1/vision/classify` + `/v1/vision/retrieve` from Results
- `/v1/vision/draft` from One-snap Draft


## Segmentation upgrade
The vision segmenter now uses a GrabCut-first path (via OpenCV) for better single-photo foreground extraction, with the prior centered-mask fallback if OpenCV is unavailable.


## Vision classification/embedding upgrade
The classifier now uses richer zero-shot prompt sets per category for stronger image-to-category matching.

New endpoint:
- `POST /v1/vision/classify_and_retrieve`
  - returns classification + image retrieval + text retrieval using the detected family


## Draft preview generation
New endpoint:
- `POST /v1/vision/preview`
  - classifies image
  - segments foreground
  - creates single-view draft metadata
  - generates a pseudo-3D preview PNG


## Lightweight rotatable preview
New endpoint:
- `POST /v1/vision/geometry_preview`
  - returns lightweight generated geometry parameters for a mobile rotatable preview

The Expo app now includes `/snap/rotatable` for a simple generated geometry viewer.


## Constrained single-photo reconstruction (v1)
New endpoint:
- `POST /v1/vision/reconstruct`

This v1 reconstructs only 6 core families:
- bracket
- hook
- clip
- handle
- enclosure
- adapter

It returns a family-aware parametric draft rather than a final mesh.


## Guided multi-angle capture
The app now supports an optional multi-angle capture mode:
- Front view in `/snap/camera`
- Guided left/right/top views in `/snap/multi-capture`

New multi-photo endpoints:
- `POST /v1/vision/classify_multi`
- `POST /v1/vision/retrieve_multi`
- `POST /v1/vision/reconstruct_multi`

v1 uses light multi-view fusion for better family confidence and reconstruction confidence.


## User corrections + profile onboarding
The mobile app now supports:
- family correction screen (`/snap/family-correction`)
- draft accept / reject telemetry
- local profile onboarding (`/onboarding/profile`) with interests + skill level

These events feed the learning pipeline and can later be connected to a real auth/profile backend.


## Printability analyzer foundation
New endpoint:
- `POST /v1/vision/printability`

Returns:
- print confidence
- risk band
- suggestions
- recommended material

## STL export foundation
New endpoint:
- `POST /v1/vision/export_stl`


## Nearby printer routing foundation
New endpoints:
- `POST /v1/printers/nearby`
- `POST /v1/printers/submit`

This is a foundation flow for finding nearby capable printers and submitting a print request.
Current printer network is seeded demo data, not a live production partner network yet.


## Design sharing foundation
New endpoints:
- `GET /v1/designs`
- `GET /v1/designs/{slug}`
- `POST /v1/designs/publish`

This provides a foundation for public design pages, in-app exploration, and external share links.
Current persistence is in-memory foundation data, not a production database yet.


## Auth + ownership foundation
New endpoints:
- `POST /v1/auth/signup`
- `POST /v1/auth/login`
- `GET /v1/me`
- `GET /v1/my-designs`
- `POST /v1/designs/{slug}/like`

This adds a basic auth/ownership layer so published designs can be linked to a creator.
Current implementation is a local file-backed foundation, not production auth.


## Creator listing support
New endpoint:
- `GET /v1/creators/{creator}`

This supports hosted creator pages and public creator-based discovery.


## Universal links / App Links foundation
Added hosted well-known files and Expo app scheme configuration foundation for:
- iOS Universal Links
- Android App Links
- App deep links using `eyeplatform://`


## Preview hosting foundation
Added:
- auto preview generation during design publish
- `POST /v1/designs/{slug}/host-preview`
- public `preview_url` support for hosted landing pages and share cards

Current implementation uses local hosted preview copies as a stand-in for S3/R2.


## Security + queue foundation
Added:
- PBKDF2 password hashing
- password strength validation
- signup/login rate limiting
- background jobs endpoints
- printer node status endpoints
- mobile queue + printer node tools


## Cloud DB + worker foundation
Added:
- Postgres adapter scaffold
- worker executor foundation
- one-shot worker run endpoint
- Postgres health endpoint
- mobile worker tool


## Deployment bundle foundation
Added:
- API Dockerfile
- production env templates
- docker compose example
- nginx reverse proxy example
- deployment checklist
- `/health` endpoint


## Beta hardening + smoke test foundation
Added:
- beta smoke test plan
- beta hardening checklist
- smoke test report template
- beta readiness summary script


## Staging verification foundation
Added:
- staging verification pass
- go/no-go template
- beta env validator
- staging readiness summary
- `/readiness` endpoint


## AI design challenges foundation
Added:
- challenge service
- challenge list/detail/submit endpoints
- mobile challenge screens
- challenge leaderboard foundation


## Prompt engine + workflow router foundation
Added:
- live-detect endpoint
- prompt engine service
- workflow routing for scan/fix/build
- premium Scan the World gating
- mobile prompt engine prototype


## Fix This Object workflow foundation
Added:
- fix-object planning endpoint
- repair Object DNA generation
- mobile Fix This Object screen
- quick repair actions for broken parts


## Camera router integration foundation
Added:
- camera routing endpoint
- direct routing from live detection to scan/fix/build workflows
- mobile camera router prototype


## AR object placement foundation
Added:
- AR placement planning endpoint
- placement surface / mode logic
- fit-check generation
- mobile AR placement planning screen
