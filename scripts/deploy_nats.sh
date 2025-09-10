#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."/nats

APP_NAME=${APP_NAME:-daily-set-nats}
VOLUME_NAME=${VOLUME_NAME:-nats_data}
REGION=${REGION:-iad}
SIZE_GB=${SIZE_GB:-1}

echo "Ensuring Fly app '$APP_NAME' exists..."
if ! fly apps list --json | grep -q '"Name":"'"$APP_NAME"'"'; then
  fly apps create "$APP_NAME" || true
fi

echo "Ensuring Fly volume '$VOLUME_NAME' exists in region '$REGION'..."
if ! fly volumes list --app "$APP_NAME" 2>/dev/null | grep -q " $VOLUME_NAME "; then
  fly volumes create "$VOLUME_NAME" --app "$APP_NAME" --region "$REGION" --size "$SIZE_GB"
fi

echo "Deploying NATS app '$APP_NAME'..."
fly deploy --app "$APP_NAME" --config fly.toml

echo
echo "NATS deployed. Use this internal URL from other Fly apps in the same org:" 
echo "  nats://$APP_NAME.internal:4222"
echo
