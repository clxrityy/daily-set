# NATS for Daily Set

This folder contains a minimal Fly app config to run a private NATS server with JetStream.

## Local development

- Start a local NATS in Docker:
  - `bash scripts/run_nats.sh`
- Connect URL for backend and realtime:
  - `NATS_URL=nats://127.0.0.1:4222`

`scripts/dev_full.sh` already exports `NATS_URL` for both services.

## Fly deployment (private network)

1. Create a volume and deploy:
   - `bash scripts/deploy_nats.sh`

Notes:

- Monitoring is exposed on port 8222 internally.
- Storage is persisted to a Fly volume at `/data`.
