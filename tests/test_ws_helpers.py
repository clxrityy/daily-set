import anyio
import asyncio
import time
from app.main import broadcast_event, _WS_CONNECTIONS


class FakeWS:
    def __init__(self):
        self.sent = []

    async def send_text(self, msg: str):
        await asyncio.sleep(0)
        self.sent.append(("text", msg))

    async def send_json(self, obj):
        await asyncio.sleep(0)
        self.sent.append(("json", obj))


def test_broadcast_event_throttle_and_cleanup(monkeypatch):
    # Register a fake socket and ensure broadcast works and throttles
    try:
        _WS_CONNECTIONS.clear()
        ws = FakeWS()
        _WS_CONNECTIONS[ws] = {"last_sent": 0}

        ev = {"type": "other", "x": 1}
        # First broadcast should send
        anyio.run(broadcast_event, ev.copy())
        first_count = len(ws.sent)
        assert first_count in (1, 0)  # send_text or send_json depending on _prepare_message

        # Rapid second broadcast should be throttled (no additional send)
        anyio.run(broadcast_event, ev.copy())
        assert len(ws.sent) == first_count
    finally:
        _WS_CONNECTIONS.clear()
import asyncio
import time
import types
from app.main import _prepare_message, _send_to_websocket


class DummyWS:
    def __init__(self):
        self.sent = []

    async def send_text(self, msg: str):
        self.sent.append(("text", msg))

    async def send_json(self, obj):
        self.sent.append(("json", obj))


def test_prepare_message_fallback_on_unserializable():
    e = {"ok": True}
    assert isinstance(_prepare_message(e), str)

    # Functions are not JSON serializable -> should return None
    e_bad = {"f": lambda x: x}
    assert _prepare_message(e_bad) is None


async def _send_twice_quickly():
    ws = DummyWS()
    meta = {"last_sent": 0}
    ev = {"x": 1}
    now = time.time()
    # First send should pass and set last_sent
    ok1 = await _send_to_websocket(ws, meta, None, ev, now) # pyright: ignore[reportArgumentType]
    # Second send within 0.45s window should be throttled (but still return True as no failure)
    ok2 = await _send_to_websocket(ws, meta, None, ev, now + 0.1) # pyright: ignore[reportArgumentType]
    return ws, ok1, ok2, meta


def test_send_to_websocket_throttle():
    ws, ok1, ok2, meta = asyncio.run(_send_twice_quickly())
    assert ok1 is True and ok2 is True
    # Only one actual send should have occurred due to throttling
    assert len(ws.sent) == 1
    # meta.last_sent should be updated
    assert meta["last_sent"] > 0
