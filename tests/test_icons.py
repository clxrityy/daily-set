from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_icons_exist_and_types():
    # Each of these should 200 if present in static dir; otherwise 404.
    # We assert 200 for the ones we ship in repo.
    resp = client.get('/favicon.ico')
    assert resp.status_code == 200
    assert resp.headers.get('content-type', '').startswith('image/')

    resp = client.get('/favicon-32x32.png')
    assert resp.status_code == 200
    assert resp.headers.get('content-type', '') == 'image/png'

    resp = client.get('/favicon-16x16.png')
    assert resp.status_code == 200
    assert resp.headers.get('content-type', '') == 'image/png'

    resp = client.get('/apple-touch-icon.png')
    assert resp.status_code == 200
    assert resp.headers.get('content-type', '') == 'image/png'

    resp = client.get('/android-chrome-192x192.png')
    assert resp.status_code == 200
    assert resp.headers.get('content-type', '') == 'image/png'

    resp = client.get('/android-chrome-512x512.png')
    assert resp.status_code == 200
    assert resp.headers.get('content-type', '') == 'image/png'
