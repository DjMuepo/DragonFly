# Eye Geometry Backend

Launchable Option A backend for Eye.

It generates a real `.glb` file immediately using procedural geometry from the detected object label. The API contract already accepts image uploads so Stable Fast 3D, TripoSR, Shap-E, Zero123, or another image-to-3D engine can replace the internals later.

## Run locally

```bash
cd geometry-backend
# Python 3.11 is the supported runtime. Python 3.12 is supported for CPU-only development.
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Health check:

```bash
curl http://localhost:8000/health
```

Generate a GLB:

```bash
curl -X POST http://localhost:8000/v1/geometry/generate \
  -H 'content-type: application/json' \
  -d '{"label":"spray bottle","confidence":0.91}'
```

## Production deploy

Use Render/Railway/Fly.io as a simple web service.

Start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Set your Expo app env:

```bash
EXPO_PUBLIC_API_BASE=https://YOUR-GEOMETRY-BACKEND.onrender.com
```

## Upgrade path to real AI mesh generation

Replace the body of `/v1/geometry/generate-from-image` with:

1. save uploaded image
2. run Stable Fast 3D / TripoSR / paid 3D API
3. export GLB to `static/models`
4. return the same response shape

The Expo app will not need routing changes.
