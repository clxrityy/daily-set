# Daily Set Frontend (React + Vite)

This is the new React frontend. It builds into the FastAPI static folder so the backend can serve it directly.

- Dev server: http://localhost:5173
- API proxy: /api -> http://127.0.0.1:8000, /ws -> ws://127.0.0.1:8000
- Build output: `app/static/dist`

## Scripts

- npm install
- npm run dev
- npm run build

## UX Notes

- Username Prefill: When a user starts a session, the chosen name is saved in `localStorage` under `ds_last_username`. On app load, the start overlay input is prefilled from `ds_last_username` if present, otherwise falls back to the previous session snapshot key `ds_session_v1.username` when available.
