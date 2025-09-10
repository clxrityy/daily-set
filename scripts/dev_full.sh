#!/usr/bin/env bash
set -euo pipefail

# Full dev: frontend build + backend + nats + realtime
# Assumes frontend has been built by Makefile before calling this script.

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

# Ensure venv and backend deps
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
. .venv/bin/activate
pip -q install -r requirements.txt

# Start NATS (if not already running)
if ! docker ps --format '{{.Names}}' | grep -q '^nats-dev$'; then
  echo "Starting NATS on ports 4222/8222/6222..."
  docker run -d --rm -p 4222:4222 -p 8222:8222 -p 6222:6222 --name nats-dev nats:latest -js >/dev/null
fi

# Start Go realtime and uvicorn in parallel; stop all on exit
cleanup() {
  pkill -P $$ || true
  # stop NATS container if we started it
  docker stop nats-dev >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

bash scripts/kill_port.sh

(
  cd realtime
  REALTIME_ADDR=":8081" NATS_URL="nats://127.0.0.1:4222" go run . 2>&1 &
)

(
  NATS_URL="nats://127.0.0.1:4222" .venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 2>&1 &
)

wait
