#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
cd realtime
export REALTIME_ADDR=${REALTIME_ADDR:-":8081"}
exec go run .
