Apply this patch in Codespaces:

cd /workspaces
unzip -o DragonFly_emergency_patch.zip -d /workspaces/DragonFly

Run backend:
cd /workspaces/DragonFly/eye-platform-alpha-geometry-backend/geometry-backend
uvicorn app.main:app --host 0.0.0.0 --port 8010

Run frontend:
cd /workspaces/DragonFly/eye-expo
npm install
npx expo start --web --clear
