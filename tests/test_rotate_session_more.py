from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine, Session as SQLSession
from app.main import app
from app import crud, game


def setup_db(tmp_path):
    db = tmp_path / 'rotmore.db'
    engine = create_engine(f'sqlite:///{db}', connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    crud.engine = engine
    return engine


def test_rotate_session_missing_token_returns_401(tmp_path):
    setup_db(tmp_path)
    client = TestClient(app)

    # create a session to obtain a sid, but use a fresh client without cookies for rotate
    r = client.post('/api/start_session', json={})
    sid = r.json().get('session_id')
    assert sid is not None

    client2 = TestClient(app)
    r2 = client2.post(f'/api/rotate_session/{sid}')
    assert r2.status_code == 401


def test_rotate_session_invalid_token_returns_403(tmp_path):
    engine = setup_db(tmp_path)
    client = TestClient(app)

    # Start a player-owned session for today
    r = client.post('/api/start_session', json={"username": "alice"})
    assert r.status_code == 200
    sid_a = r.json().get('session_id')
    assert sid_a is not None

    # Create a different session directly via CRUD for another date and sign its token
    with SQLSession(engine) as s:
        other_board = game.daily_board('2025-01-01')
        gs_b = crud.create_session(s, None, '2025-01-01', other_board)
        assert gs_b.id is not None
        bad_token = crud.sign_session_token(s, gs_b.id)

    # Call rotate for sid_a but present Authorization for gs_b -> 403 (unauthorized token)
    r2 = client.post(f'/api/rotate_session/{sid_a}', headers={"Authorization": f"Bearer {bad_token}"})
    assert r2.status_code == 403


def test_rotate_session_missing_player_token_for_owned_session(tmp_path):
    setup_db(tmp_path)
    client = TestClient(app)

    # Start a session with username to ensure session has a player_id
    r = client.post('/api/start_session', json={"username": "owner"})
    assert r.status_code == 200
    sid = r.json().get('session_id')
    tok = r.json().get('session_token')
    assert sid and tok

    # Use a new client with only Authorization header (no player_token cookie) -> 403
    client2 = TestClient(app)
    r2 = client2.post(f'/api/rotate_session/{sid}', headers={"Authorization": f"Bearer {tok}"})
    assert r2.status_code == 403
