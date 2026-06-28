# Eye Alpha: Run + Deploy

## 1. Run geometry backend locally

```bash
cd geometry-backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Check:

```bash
curl http://localhost:8000/health
```

Generate GLB:

```bash
curl -X POST http://localhost:8000/v1/geometry/generate \
  -H 'content-type: application/json' \
  -d '{"label":"spray bottle","confidence":0.91}'
```

## 2. Run Expo app

```bash
cd eye-expo
cp .env.example .env
# Edit .env if your backend is not localhost
npm install
npx expo start --web --clear
```

Required app env:

```bash
EXPO_PUBLIC_API_BASE=http://localhost:8000
```

Optional AI vision env:

```bash
EXPO_PUBLIC_OPENAI_API_KEY=sk-...
EXPO_PUBLIC_OPENAI_VISION_MODEL=gpt-4.1-mini
```

If OpenAI quota fails or the key is missing, the app still demos with fallback detection.

## 3. Deploy backend

Fast path: Render or Railway.

Backend start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Health path:

```bash
/health
```

After deployment, set the Expo web env:

```bash
EXPO_PUBLIC_API_BASE=https://YOUR-BACKEND-DOMAIN
```

## 4. Deploy Expo web

```bash
cd eye-expo
npm install
npx expo export --platform web
```

Deploy the generated web output to Vercel/Netlify/Cloudflare Pages.

## Current launch scope

This build is launchable as Eye Alpha:

- one-photo capture
- cutout stage
- AI object detection with fallback
- geometry backend contract
- procedural GLB generation from detected object label
- result/download/preview flow

## Next engine swap

Replace backend internals in:

```bash
geometry-backend/app/main.py
/v1/geometry/generate-from-image
```

with Stable Fast 3D, TripoSR, Shap-E, Zero123++, or a paid image-to-3D API.
The Expo app does not need route changes.
