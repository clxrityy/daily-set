from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine
from app.main import app, SubmitSetRequest, _validate_username_param, _validate_date_param
from app import crud


def setup_db(tmp_path):
    db = tmp_path / 'submit_helpers.db'
    engine = create_engine(f'sqlite:///{db}', connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    crud.engine = engine


def test_validate_username_and_date():
    assert _validate_username_param("abc") == "abc"
    for bad in ["", " ", "aaa bbb", "x"*13]:
        try:
            _validate_username_param(bad)
            assert False, "should raise"
        except Exception:
            pass

    assert _validate_date_param("2025-09-09") == "2025-09-09"
    for bad in ["2025/09/09", "2025-9-9", "abc"]:
        try:
            _validate_date_param(bad)
            assert False
        except Exception:
            pass


def test_submit_set_error_branches(tmp_path):
    setup_db(tmp_path)
    client = TestClient(app)

    # Create player and session
    r = client.post('/api/player', json={"username": "zoe", "password": "GoodPass1"})
    assert r.status_code == 201
    # Start a session via /api/start_session to obtain a session_id
    r2 = client.post('/api/start_session', json={"username": "zoe"})
    assert r2.status_code == 200
    sid = r2.json()["session_id"]

    # Invalid indices length
    rr = client.post('/api/submit_set', json={"session_id": sid, "indices": [0, 1]})
    assert rr.status_code in (400, 422)

    # Duplicate indices
    rr = client.post('/api/submit_set', json={"session_id": sid, "indices": [0, 0, 1]})
    assert rr.status_code in (400, 422)

    # Out of range
    rr = client.post('/api/submit_set', json={"session_id": sid, "indices": [99, 100, 101]})
    assert rr.status_code == 400
