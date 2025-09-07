import json
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_start_session_username_max_length():
    # 13 chars should fail
    resp = client.post('/api/start_session', json={"username": "ABCDEFGHIJKLM"})
    assert resp.status_code == 422

    # 12 chars should pass
    resp = client.post('/api/start_session', json={"username": "ABCDEFGHIJKL"})
    assert resp.status_code in (200, 403)  # if already completed, API may 403


def test_start_session_username_sanitization():
    # Disallow unsafe characters
    resp = client.post('/api/start_session', json={"username": "bad<script>"})
    assert resp.status_code == 422

    # Allow underscores and hyphens
    resp = client.post('/api/start_session', json={"username": "good_name-1"})
    assert resp.status_code in (200, 403)


def test_submit_set_username_validation():
    # Invalid username should 422
    resp = client.post('/api/submit_set', json={"username": "x" * 51, "indices": [0,1,2]})
    assert resp.status_code == 422

    # Valid username optional
    resp = client.post('/api/submit_set', json={"indices": [0,1,2]})
    assert resp.status_code in (200, 400)  # depends on indices validity
