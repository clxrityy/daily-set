#!/usr/bin/env bash
set -euo pipefail

# Deploy Daily Set to Fly.io
# - Builds the frontend
# - Ensures Python deps are installed (optional)
# - Runs `fly deploy` using fly.toml in repo root

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"

echo "[deploy] Building frontend…"
pushd "$ROOT/frontend" >/dev/null
npm ci || npm install
npm run build
popd >/dev/null

echo "[deploy] Running fly deploy…"
cd "$ROOT"
fly deploy

echo "[deploy] Done."
