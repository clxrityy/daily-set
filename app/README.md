# Daily Set Backend (FastAPI)

FastAPI app powering the Daily Set game. Serves the React build, REST APIs, and a simple WebSocket broadcast for live updates. Optionally publishes events to NATS for the Go realtime gateway.

## Features

- FastAPI + SQLModel, SQLite by default
- Static hosting for built frontend under `/static/dist`
- REST APIs for daily board, sessions, leaderboard, and found sets
- WebSocket endpoint at `/ws` with per-connection rate limiting
- Optional NATS publish: backend → `room.<room>.update` (for Go gateway fanout)
- Structured JSON logging, security headers, basic CORS, and simple rate limiting

## Quick start (dev)

```bash
# From repo root
make dev
# -> starts: backend on http://127.0.0.1:8000, local NATS, and Go realtime on :8081
```

Direct backend only:

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python -m app.init_db
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Environment variables

- DATABASE_URL: DB URL (default `sqlite:///./set.db`)
- COOKIE_SECURE: `1` to set `Secure` on auth cookies (prod), default `0`
- NATS_URL: if set, backend publishes updates to NATS (e.g. `nats://127.0.0.1:4222` locally or `nats://daily-set-nats.internal:4222` on Fly)
- ENABLE_TEST_ENDPOINTS: `1` enables WS test hook used by tests

## Key endpoints

- GET `/` → serves SPA (`/static/dist/index.html`)
- GET `/health` → `{ "status": "ok" }`
- GET `/api/daily` → current day board
- POST `/api/player_json` → create/update player (JSON)
- GET `/api/leaderboard?date=YYYY-MM-DD&limit=20`
- GET `/api/found_sets?date=YYYY-MM-DD&player_id=...`
- POST `/api/start_session` → starts a session
- GET `/api/status` → status for current session
- GET `/api/session` → fetch session (by cookie or query)
- POST `/api/rotate_session/{session_id}` → rotate session token
- WS `/ws` → backend WebSocket (see below)

## WebSocket (`/ws`)

- Maintains a simple connection and accepts client pings; broadcasts server events to all clients.
- Server throttles sends per-connection (~0.45s min interval).
- Event payloads are plain JSON objects; completion events include `username` and top `leaders` enrichment.

## Realtime via NATS (optional)

When `NATS_URL` is set:

- Backend publishes envelopes to `room.<room>.update` where `room = daily-YYYYMMDD` (or `broadcast` fallback).
- The Go gateway subscribes to `room.*.update` and fans out to clients connected to `/ws` on the gateway.

Local/dev values:

- NATS_URL: `nats://127.0.0.1:4222` (started by `make dev`)

Fly (prod) values:

- NATS_URL: `nats://daily-set-nats.internal:4222` (private Fly network)

## CORS and security

- CORS allows origins for local dev and `https://daily-set.fly.dev` (see `app/main.py`).
- Security headers: CSP, HSTS, COOP, etc. applied via middleware.
- Cookies default to `SameSite=Lax`; set `COOKIE_SECURE=1` in production.

## Logging

- Structured JSON logs with request context and timing.
- `X-Request-ID` is set on responses for correlation.

## Testing

```bash
# Backend only tests
make test-backend

# All tests (backend + frontend)
make test
```

## Deployment (Fly.io)

- Root `fly.toml` defines the backend app (`daily-set`).
- Build frontend: `make frontend-build` (also run by `make deploy`).
- Set secrets as needed (examples):

```bash
fly secrets set NATS_URL=nats://daily-set-nats.internal:4222
fly secrets set COOKIE_SECURE=1
```

Health check: `GET https://daily-set.fly.dev/health`.

## Troubleshooting

- No realtime updates? Ensure `NATS_URL` is set for both backend and the realtime gateway, and that NATS is reachable.
- CORS blocked? Verify the allowed origins list in `app/main.py`.
- SQLite locks in dev? Quit stale processes or remove `set.db` and re-init via `python -m app.init_db`.
