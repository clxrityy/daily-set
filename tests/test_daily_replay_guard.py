from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine
from app.main import app
from app import crud


def setup_db(tmp_path):
    db = tmp_path / 'replay_guard.db'
    engine = create_engine(f'sqlite:///{db}', connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    crud.engine = engine


def test_cannot_start_or_resume_after_completion(tmp_path):
    setup_db(tmp_path)
    client = TestClient(app)
    # Reset rate limiter across tests
    import app.main as app_main
    app_main._RATE_LIMIT_STORE.clear()

    # Create player and start a session
    r = client.post('/api/player', json={"username": "bob", "password": "GoodPass1"})
    assert r.status_code == 201

    r2 = client.post('/api/start_session', json={"username": "bob"})
    assert r2.status_code == 200

    # Complete today's game for this player
    rc = client.post('/api/complete', json={"username": "bob", "seconds": 120, "date": ""})
    assert rc.status_code == 200

    # After completion, getting current session should report no active session
    rs = client.get('/api/session')
    assert rs.status_code == 200
    assert rs.json().get('active') is False

    # Starting a new session should be forbidden
    r3 = client.post('/api/start_session', json={"username": "bob"})
    assert r3.status_code == 403
    assert 'Already completed' in r3.json().get('detail', '')


def test_submit_rejected_after_completion(tmp_path):
    setup_db(tmp_path)
    client = TestClient(app)
    # Reset rate limiter across tests
    import app.main as app_main
    app_main._RATE_LIMIT_STORE.clear()

    # Create player and start a session
    r = client.post('/api/player', json={"username": "kate", "password": "GoodPass1"})
    assert r.status_code == 201
    r2 = client.post('/api/start_session', json={"username": "kate"})
    assert r2.status_code == 200
    sid = r2.json()["session_id"]

    # Mark completion for today
    rc = client.post('/api/complete', json={"username": "kate", "seconds": 80, "date": ""})
    assert rc.status_code == 200

    # Any further submit_set should be blocked (even if they still hold a session id)
    rr = client.post('/api/submit_set', json={"session_id": sid, "indices": [0, 1, 2]})
    assert rr.status_code in (400, 403)
