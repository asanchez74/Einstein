"""Tests des endpoints HTTP."""

from fastapi.testclient import TestClient

from einstein_core.main import app

client = TestClient(app)


def test_liveness() -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness() -> None:
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_version() -> None:
    response = client.get("/version")

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "Einstein Core"
    assert payload["version"] == "0.1.0"
    assert payload["environment"] == "development"
