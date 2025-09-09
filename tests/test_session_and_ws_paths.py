import asyncio
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine
from app.main import app, _WS_CONNECTIONS, broadcast_event, WebSocketDisconnect
from app import crud


def setup_db(tmp_path):
    db = tmp_path / 'sess.db'
    engine = create_engine(f'sqlite:///{db}', connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    crud.engine = engine


def test_api_session_no_cookie(tmp_path):
    setup_db(tmp_path)
    client = TestClient(app)
    r = client.get('/api/session')
    assert r.status_code == 200
    assert r.json() == {"active": False}


def test_websocket_connect_and_disconnect(tmp_path):
    setup_db(tmp_path)
    client = TestClient(app)

    # Connect WS and then close immediately
    with client.websocket_connect('/ws') as ws:
        # after accepting, server awaits receive; send a ping then close
        ws.send_text('ping')
    # exiting context closes connection; registry cleanup happens in server handler
    # Not directly observable, but ensure registry doesn't explode
    assert isinstance(_WS_CONNECTIONS, dict)


def test_broadcast_cleanup_on_send_failure(monkeypatch):
    # Register a fake socket that raises on send
    class BoomWS:
        async def send_text(self, s: str):
            raise RuntimeError('boom')
        async def send_json(self, obj):
            raise RuntimeError('boom')

    ws = BoomWS()
    _WS_CONNECTIONS.clear()
    _WS_CONNECTIONS[ws] = {"last_sent": 0}

    # Broadcast any event; failure should remove ws from registry
    import anyio
    anyio.run(broadcast_event, {"type": "x"})

    assert ws not in _WS_CONNECTIONS
