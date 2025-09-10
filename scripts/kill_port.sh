#!/usr/bin/env bash

kill_port() {
  local PORT="$1"
  # macOS: lsof present by default
  PIDS=$(lsof -ti tcp:${PORT} -sTCP:LISTEN 2>/dev/null || true)
  if [ -n "$PIDS" ]; then
    echo "Freeing port :${PORT} (PIDs: $PIDS)"
    kill -TERM $PIDS 2>/dev/null || true
    sleep 0.5
    # Force kill if still alive
    PIDS2=$(lsof -ti tcp:${PORT} -sTCP:LISTEN 2>/dev/null || true)
    if [ -n "$PIDS2" ]; then
      kill -KILL $PIDS2 2>/dev/null || true
    fi
  fi
}

# Ensure ports are free for a re-run
kill_port 8081
kill_port 8000