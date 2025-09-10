#!/usr/bin/env bash
set -euo pipefail
# Run a local NATS server with JetStream enabled
exec docker run --rm -p 4222:4222 -p 8222:8222 -p 6222:6222 --name nats-dev nats:latest -js
