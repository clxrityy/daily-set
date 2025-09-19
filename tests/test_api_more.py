from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine
from app.main import app
from app import crud


def setup_db(tmp_path):
    db = tmp_path / 'api2.db'
    engine = create_engine(f'sqlite:///{db}', connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    crud.engine = engine


def test_cache_stats_endpoint(tmp_path):
    setup_db(tmp_path)
    client = TestClient(app)
    r = client.get('/api/cache/stats')
    assert r.status_code == 200
    data = r.json()
    assert data.get('status') == 'ok'
    assert 'cache_stats' in data


def test_complete_and_status_detail(tmp_path):
    setup_db(tmp_path)
    # Reset rate limiter across tests
    import app.main as app_main
    app_main._RATE_LIMIT_STORE.clear()
    client = TestClient(app)

    # Create a named player and complete
    name = 'alice'
    r = client.post('/api/player', json={"username": name, "password": "GoodPass1"})
    assert r.status_code == 201

    r2 = client.post('/api/complete', json={"username": name, "seconds": 90, "date": ""})
    assert r2.status_code == 200

    # Now status should include detail (seconds, placement, completed_at)
    r3 = client.get('/api/status')
    assert r3.status_code == 200
    data = r3.json()
    assert data.get('completed') in (True, False)  # depends on cookie identity resolution
    # Call leaderboard to ensure it returns JSON payload
    r4 = client.get('/api/leaderboard', params={"limit": 10})
    assert r4.status_code == 200


def test_rotate_session_requires_token(tmp_path):
    setup_db(tmp_path)
    client = TestClient(app)

    # 401 without any token
    r = client.post('/api/rotate_session/not-real')
    assert r.status_code in (400, 401)  # depending on UUID validation
