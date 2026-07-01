# SpyCam Scanner

SpyCam Scanner is a React dashboard backed by a FastAPI API. The frontend lives in `frontend/`; the scanner API and SQLite storage live in `backend/`.

Important deployment note: a backend hosted on Render runs inside Render's cloud network, not on the user's Wi-Fi. It can host the app and persist scan history, but it cannot directly scan a private LAN such as `192.168.1.0/24` from a user's phone. For real local-network scanning, run the backend on a machine inside the same network, or add a local agent that reports to the hosted API.

## Local Development

Backend:

```bash
cd backend
pip install -r requirements.txt
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Set `frontend/.env` from `frontend/.env.example` if the API is not on `http://localhost:8000`.

## Deploying On Render

The repo includes `render.yaml`, so the easiest path is Render Blueprints:

1. Push this repository to GitHub/GitLab.
2. In Render, create a new Blueprint from the repo.
3. Render will create:
   - `spy-scanner-api`: FastAPI web service from `backend/`.
   - `spy-scanner-web`: static React site from `frontend/`.
4. After the first deploy, open the API service and set `CORS_ORIGINS` to the frontend URL, for example `https://spy-scanner-web.onrender.com`. The blueprint starts with `*` so the first deploy works, but the production value should be tighter.
5. Confirm the frontend has `REACT_APP_BACKEND_URL` set to the API service URL, for example `https://spy-scanner-api.onrender.com`.

Manual Render settings if you do not use the blueprint:

Backend web service:

```text
Root Directory: backend
Runtime: Python
Build Command: pip install -r requirements.txt
Start Command: uvicorn server:app --host 0.0.0.0 --port $PORT
Health Check Path: /api/
Environment:
  DATABASE_PATH=/var/data/spy_scanner.db
  CORS_ORIGINS=https://your-frontend.onrender.com
Disk:
  Mount Path: /var/data
```

Frontend static site:

```text
Root Directory: frontend
Build Command: npm ci && npm run build
Publish Directory: build
Environment:
  REACT_APP_BACKEND_URL=https://your-api.onrender.com
Rewrite:
  Source: /*
  Destination: /index.html
```

## Mobile Optimizations

The app shell switches from a desktop sidebar to a bottom navigation on phones, the scanner controls stay visible on small screens, device results use touch-friendly cards on mobile, long network identifiers wrap safely, and reduced-motion preferences are respected.
