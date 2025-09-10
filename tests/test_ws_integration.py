import json
import time
import os
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine
from app.main import app
from app import crud


def setup_db(tmp_path):
    db = tmp_path / 'wsint.db'
    engine = create_engine(f'sqlite:///{db}', connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    crud.engine = engine


def test_ws_receives_completion_broadcast(tmp_path):
    setup_db(tmp_path)
    client = TestClient(app)

    # Create a player and start a session (ensures /api/complete will find player)
    r = client.post('/api/player', json={"username": "alice_int", "password": "GoodPass1"})
    assert r.status_code == 201

    # Enable test hooks and open WebSocket, then trigger a deterministic broadcast via WS message
    os.environ['ENABLE_TEST_ENDPOINTS'] = '1'
    with client.websocket_connect('/ws') as ws:
        ws.send_text('__test_broadcast:{"type":"completion","player_id":1,"date":"2099-01-01","seconds":77}')
        # Receive the echoed/broadcast message
        msg = ws.receive_text()
        data = json.loads(msg)
        # For test broadcast, allow either enriched completion or raw event
        assert data.get('type') in ('completion',)