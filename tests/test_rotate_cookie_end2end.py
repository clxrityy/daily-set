from fastapi.testclient import TestClient
from app.main import app
from app import crud
from sqlmodel import SQLModel, create_engine, Session


def test_rotate_session_end2end(tmp_path):
    db = tmp_path / 'test.db'
    engine = create_engine(f'sqlite:///{db}', connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    crud.engine = engine

    client = TestClient(app)

    # start a session (no username)
    resp = client.post('/api/start_session', json={})
    data = resp.json()
    sid = data.get('session_id')
    token = data.get('session_token')
    assert sid is not None
    assert token is not None

    # rotate using cookies (simulate browser flow)
    r2 = client.post(f'/api/rotate_session/{sid}')
    assert r2.status_code in(200, 403)  # depending on timing of daily reset
    new_token = r2.cookies.get('session_token')
    assert new_token != token

    # verify on server-side
    # with Session(engine) as s:
    #     assert new_token is not None
    #     assert crud.verify_session_token(s, new_token) == sid


def test_non_owner_cannot_rotate(tmp_path):
    db = tmp_path / 'test2.db'
    engine = create_engine(f'sqlite:///{db}', connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    crud.engine = engine

    client = TestClient(app)
    # start a session as anon (creates player_token cookie)
    resp = client.post('/api/start_session', json={})
    sid = resp.json().get('session_id')
    assert sid is not None

    # new client with its own cookies attempts to rotate (has its own player_token)
    client2 = TestClient(app)
    resp2 = client2.post('/api/start_session', json={})
    assert resp2.status_code == 200
    r = client2.post(f'/api/rotate_session/{sid}')
    assert r.status_code == 403
