# EYE Platform (Expo MVP)

This is an Expo (React Native) MVP implementing the **Snap & Copy** flow:

- Splash → Home
- Snap & Copy: Camera → Cutout Check → Matches (polled from backend) → Edit → Print Ready

## Run the backend

See `../api/README.md`.

## Run the mobile app

1. Install Node.js 18+
2. Install dependencies:

```bash
npm install
```

3. Start the app.

If you're using a simulator and the backend is on the same machine:

```bash
npm run start
```

If you're using a physical phone, set the API base URL to your LAN IP:

```bash
EXPO_PUBLIC_API_BASE=http://YOUR_LAN_IP:8000 npm run start
```

## What works in this MVP

- Camera capture (hero + silent burst captured locally)
- Creates a backend job + uploads the hero image
- Matches screen polls the backend for results

## What is mocked for now

- Retrieval results (matches) are mocked server-side
- Draft mesh generation + exports return a dummy STL

Next steps are to swap mocked services for real retrieval + reconstruction.
