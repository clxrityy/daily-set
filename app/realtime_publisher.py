"""
Realtime publisher: Publishes events to NATS for the Go realtime gateway.
If NATS is not configured, all functions are safe no-ops.
"""
from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Any, Optional

_nc = None  # type: ignore

try:
    import nats
except Exception:  # pragma: no cover - optional dep
    nats = None  # type: ignore


async def _connect_once() -> None:
    global _nc
    if _nc or not nats:
        return
    url = os.getenv("NATS_URL")
    if not url:
        return
    try:
        _nc = await nats.connect(url, name="daily-set-python")
    except Exception:
        _nc = None


async def publish_room_update(room: str, payload: dict[str, Any]) -> None:
    """Publish an update message to a room subject.

    Subject: room.<room>.update
    """
    await _connect_once()
    if not _nc:
        return
    env = {
        "v": 1,
        "type": "update",
        "room": room,
        "id": payload.get("id") or os.urandom(8).hex(),
        "ts": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
    }
    try:
        await _nc.publish(f"room.{room}.update", json.dumps(env).encode("utf-8"))
    except Exception:
        pass


def publish_room_update_sync(room: str, payload: dict[str, Any]) -> None:
    """Sync helper that runs the async publisher. Safe if no loop or NATS."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(publish_room_update(room, payload))
        return
    loop.create_task(publish_room_update(room, payload))
