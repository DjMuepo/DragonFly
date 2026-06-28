# Eye Platform MVP - Deploy Now

This package is set up as a one-photo-first deployed MVP.

## Working flow

Camera -> Cutout -> AI Processing -> Generate 3D -> 3D Result -> 3D Preview / Download placeholder / New Scan

## Run locally in Codespaces

```bash
cd /workspaces/3Tests/eye-expo
npm install
npx expo start --web --clear
```

If you are using this zip directly:

```bash
cd eye-expo
npm install
npx expo start --web --clear
```

## Optional AI key

Create `eye-expo/.env`:

```bash
EXPO_PUBLIC_OPENAI_API_KEY=sk-your-key
EXPO_PUBLIC_OPENAI_VISION_MODEL=gpt-4.1-mini
```

If no key is set or quota fails, the app still runs using fallback detection so the demo does not break.

## Web export

```bash
cd eye-expo
npm install
npx expo export --platform web
```

Upload the generated `dist/` folder to Vercel, Netlify, Cloudflare Pages, or your existing server.

## What is production-ready in this MVP

- Stable one-photo scan flow
- Working camera handoff
- Cutout stage
- AI object detection with fallback
- Generate 3D progress stage
- Result screen
- Preview screen
- Button routes wired
- Safe fallback if OpenAI API is missing or out of quota

## What is intentionally stubbed for the next backend pass

- True SAM/Grounded-SAM background removal
- Real single-image mesh reconstruction
- Real GLB/OBJ download
- Cloud user accounts and saved scan library
