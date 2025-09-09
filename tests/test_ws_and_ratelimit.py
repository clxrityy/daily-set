import json
import asyncio
from starlette.requests import Request
from sqlmodel import SQLModel, create_engine, Session as SQLSession

from app.main import check_rate_limit, broadcast_event
from app import crud, game


def setup_db(tmp_path):
    db = tmp_path / 'ws.db'
    engine = create_engine(f'sqlite:///{db}', connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    crud.engine = engine


def test_websocket_broadcast_enrichment(tmp_path):
    # Reset rate limiter across tests to avoid 429s
    import app.main as app_main
    app_main._RATE_LIMIT_STORE.clear()
    setup_db(tmp_path)

    # Seed DB with a player and a completion for today
    with SQLSession(crud.engine) as s:
        p = crud.create_player(s, 'alice', 'GoodPass1')
        assert p is not None and p.id is not None
        pid = int(p.id)
        today = game.today_str()
        crud.record_time(s, pid, today, 42)

    # Use a fake WebSocket to capture broadcast without relying on TestClient's event loop
    class FakeWS:
        def __init__(self):
            self.texts = []
            self.jsons = []
        async def send_text(self, s: str):
            await asyncio.sleep(0)
            self.texts.append(s)
        async def send_json(self, obj):
            await asyncio.sleep(0)
            self.jsons.append(obj)

    fake = FakeWS()
    import app.main as app_main
    app_main._WS_CONNECTIONS = {fake: {'player_id': None, 'last_sent': 0}}

    # Trigger a completion event and run broadcast
    event = {"type": "completion", "player_id": pid, "date": today, "seconds": 42}
    import anyio
    anyio.run(broadcast_event, event)

    # Validate one message was sent and enriched
    assert len(fake.texts) + len(fake.jsons) >= 1
    if fake.texts:
        data = json.loads(fake.texts[0])
    else:
        data = fake.jsons[0]
    assert data.get('type') == 'completion'
    assert data.get('username') == 'alice'
    leaders = data.get('leaders')
    assert isinstance(leaders, list)
    assert any(l.get('username') == 'alice' for l in leaders)


def test_rate_limit_window_edges(monkeypatch):
    # Reset global store
    import app.main as app_main
    app_main._RATE_LIMIT_STORE.clear()

    # Control time
    t = [1000.0]
    monkeypatch.setattr(app_main.time, 'time', lambda: t[0])

    # Build a minimal Request with a client IP
    async def _dummy_receive():
        await asyncio.sleep(0)
        return {"type": "http.request"}
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [],
        "query_string": b"",
        "server": ("testserver", 80),
        "client": ("1.2.3.4", 12345),
        "scheme": "http",
    }
    req = Request(scope, _dummy_receive)

    # Allow up to 3 in window
    assert check_rate_limit(req, max_requests=3, window_seconds=10) is True
    assert check_rate_limit(req, max_requests=3, window_seconds=10) is True
    assert check_rate_limit(req, max_requests=3, window_seconds=10) is True
    # Next one within window should be limited
    assert check_rate_limit(req, max_requests=3, window_seconds=10) is False

    # Advance beyond window; old entries should be pruned, allowing new request
    t[0] += 11
    assert check_rate_limit(req, max_requests=3, window_seconds=10) is True
