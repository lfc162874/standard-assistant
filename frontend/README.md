# Frontend

## Run locally

```bash
cp .env.example .env
npm install
npm run dev
```

Default URL: `http://localhost:5173`

## Backend integration notes

- Frontend uses `/api` proxy to `http://127.0.0.1:8000` in dev mode.
- You can override proxy target by editing `VITE_DEV_PROXY_TARGET` in `.env`.
- Ensure backend is running before testing chat requests.
- Health check endpoint used by the page: `GET /api/v1/health`
- Chat page uses streaming endpoint by default: `POST /api/v1/chat/stream`
