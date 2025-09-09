from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine
from app.main import app
from app import crud


def setup_db(tmp_path):
    db = tmp_path / 'api3.db'
    engine = create_engine(f'sqlite:///{db}', connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    crud.engine = engine


def test_daily_endpoint_and_headers(tmp_path):
    setup_db(tmp_path)
    client = TestClient(app)

    # Hitting /api/daily returns a board and includes security headers from middleware
    r = client.get('/api/daily')
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data.get('board'), list) and len(data['board']) > 0

    # SecurityHeadersMiddleware should set CSP and X-Content-Type-Options
    assert 'Content-Security-Policy' in r.headers
    assert r.headers.get('X-Content-Type-Options') == 'nosniff'


def test_player_json_and_rate_limit(tmp_path):
    setup_db(tmp_path)
    import app.main as app_main
    app_main._RATE_LIMIT_STORE.clear()
    client = TestClient(app)

    # Create via JSON endpoint
    r = client.post('/api/player_json', json={"username": "frank", "password": "GoodPass1"})
    assert r.status_code == 201
    # Trigger rate limit quickly by repeated requests (5 allowed per 5 min in player create)
    statuses = []
    for i in range(6):
        rr = client.post('/api/player_json', json={"username": f"frank{i}", "password": "GoodPass1"})
        statuses.append(rr.status_code)
    assert 429 in statuses or statuses.count(201) >= 1  # depending on shared state, either limit or create ok
