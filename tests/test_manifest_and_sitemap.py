from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_sitemap_and_manifest():
    # sitemap.xml present in static and served at /sitemap.xml
    r = client.get('/sitemap.xml')
    assert r.status_code == 200
    assert r.headers.get('content-type', '').startswith('application/xml')

    # manifest served at /manifest.webmanifest (alias to site.webmanifest)
    r = client.get('/manifest.webmanifest')
    assert r.status_code == 200
    assert r.headers.get('content-type', '').startswith('application/manifest+json')
