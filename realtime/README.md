# Daily Set Realtime (Go)

A lightweight WebSocket gateway in Go that bridges clients to backend events via NATS.

- Endpoint: /ws
- Auth: optional JWT via Authorization: Bearer <token> or ?token=
- Broker: NATS (optional in dev)

## Env

- REALTIME_ADDR=:8081
- REALTIME_JWT_SECRET=devsecret (optional)
- NATS_URL=nats://localhost:4222 (optional)

## Message Envelope

{
"v": 1,
"type": "action|update|presence|subscribe",
"room": "room-id",
"from": "user-id",
"id": "uuid",
"ts": "ISO-8601",
"payload": {}
}

## Subjects

- room.<room>.action (client->backend)
- room.<room>.update (backend->clients)

## Build & Run

- go build ./realtime && ./realtime
- Container: see Dockerfile in this folder

## Deploy on Fly.io (separate app)

Option A: Deploy realtime as its own Fly app

1. Install flyctl and login.
2. From this folder (`realtime/`), configure:
   - Set secrets: `fly secrets set REALTIME_JWT_SECRET=...`
   - Set `NATS_URL` in `[env]` or with `fly secrets set NATS_URL=...`.
3. Deploy:
   - `fly deploy --app daily-set-realtime`
4. Health check: GET `https://daily-set-realtime.fly.dev/health`
5. Frontend WS URL: `wss://daily-set-realtime.fly.dev/ws`
