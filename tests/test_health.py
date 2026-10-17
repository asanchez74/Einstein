"""Tests des endpoints HTTP."""

import logging

import pytest
from fastapi.testclient import TestClient

from einstein_core.config import Settings
from einstein_core.main import create_app

@pytest.fixture
def app(tmp_path):
    path = tmp_path / "inventory.json"
    path.write_text("[]")
    return create_app(Settings(maison_inventory_path=path))


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client


def test_liveness(client) -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness(client) -> None:
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_version(client) -> None:
    response = client.get("/version")

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "Einstein Core"
    assert payload["version"] == "0.1.0"
    assert payload["environment"] == "development"


def test_lifespan_logs_startup_and_shutdown(caplog, app) -> None:
    with caplog.at_level(logging.INFO, logger="einstein_core.main"):
        with TestClient(app) as client:
            assert client.get("/health/ready").status_code == 200
            messages = [
                record.getMessage()
                for record in caplog.records
                if record.name == "einstein_core.main"
            ]
            assert len(messages) == 1
            assert messages[0].startswith("Einstein Core démarre")

    messages = [
        record.getMessage()
        for record in caplog.records
        if record.name == "einstein_core.main"
    ]
    assert len(messages) == 2
    assert messages[1] == "Einstein Core s'arrête"
