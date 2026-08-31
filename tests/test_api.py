from fastapi.testclient import TestClient

from ga4_platform.api import app


def test_health():
    response = TestClient(app).get("/api/health")
    assert response.status_code == 200
    assert response.json()["source"].startswith("Google official")

