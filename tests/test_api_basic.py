from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine, Session
from app.main import app
from app import crud, game
import json


def setup_db(tmp_path):
    db = tmp_path / 'api.db'
    engine = create_engine(f'sqlite:///{db}', connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    crud.engine = engine
    return engine


def test_health_and_static(tmp_path):
    setup_db(tmp_path)
    client = TestClient(app)

    r = client.get('/health')
    assert r.status_code == 200
    assert r.json().get('status') == 'ok'

    # robots and sitemap return 404 in dev if missing
    assert client.get('/robots.txt').status_code in (200, 404)
    assert client.get('/sitemap.xml').status_code in (200, 404)


def test_status_and_session_flow(tmp_path):
    setup_db(tmp_path)
    client = TestClient(app)

    # Initially, no player cookie -> completed false
    r = client.get('/api/status')
    assert r.status_code == 200
    data = r.json()
    assert data['completed'] is False

    # Start session -> sets cookies
    r2 = client.post('/api/start_session', json={})
    assert r2.status_code == 200

    # Now status should still be false, but we can fetch session
    r3 = client.get('/api/session')
    assert r3.status_code == 200
    sdata = r3.json()
    assert sdata is not None


def test_found_sets_and_leaderboard_param_validation(tmp_path):
    setup_db(tmp_path)
    client = TestClient(app)

    # found_sets with invalid username
    assert client.get('/api/found_sets', params={"username": "bad script"}).status_code == 400

    # found_sets with ok username no data -> empty list
    ok = client.get('/api/found_sets', params={"username": "alice"})
    assert ok.status_code == 200
    assert ok.json()["sets"] == []

    # leaderboard invalid date or limit (regex mismatch – slashes instead of dashes)
    assert client.get('/api/leaderboard', params={"date": "2025/13/01"}).status_code == 400
    assert client.get('/api/leaderboard', params={"limit": 0}).status_code == 400


def test_submit_set_error_paths(tmp_path):
    setup_db(tmp_path)
    client = TestClient(app)

    # Submit without indices -> 422 by pydantic, or 400 by our checks with wrong shapes
    r = client.post('/api/submit_set', json={"indices": [0,0,0]})
    assert r.status_code in (400, 422)

    # Start a session to get a board and token
    r2 = client.post('/api/start_session', json={})
    assert r2.status_code == 200
    token = r2.json().get('session_token')

    # Use out-of-range index
    r3 = client.post('/api/submit_set', json={"session_token": token, "indices": [100,101,102]})
    assert r3.status_code == 400

    # Use non-set indices on current board: pick first three, likely invalid as a set
    r4 = client.post('/api/submit_set', json={"session_token": token, "indices": [0,1,2]})
    assert r4.status_code in (200, 400)
