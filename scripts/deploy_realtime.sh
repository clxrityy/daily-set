#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
cd realtime
# Ensure we can build
go build -o /tmp/realtime-check .
rm -f /tmp/realtime-check
# Deploy with Fly (requires flyctl login and app created)
# You can set app name via FLY_APP, default daily-set-realtime
APP_NAME=${FLY_APP:-daily-set-realtime}
# flyctl will read fly.toml in this directory
exec fly deploy --app "$APP_NAME"
