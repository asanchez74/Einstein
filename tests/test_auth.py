"""Authentification à compte unique : empreinte, sessions, limitation, protection des routes."""

import pytest
from fastapi.testclient import TestClient

from einstein_core import auth
from einstein_core.config import Settings
from einstein_core.main import create_app

PASSWORD = "correct horse battery staple"


@pytest.fixture(scope="module")
def encoded():
    return auth.hash_password(PASSWORD)


@pytest.fixture
def settings(tmp_path, encoded):
    inventory = tmp_path / "inventory.json"
    inventory.write_text("[]")
    secret = tmp_path / "password_hash"
    secret.write_text(encoded + "\n")
    return Settings(maison_inventory_path=inventory, auth_enabled=True,
                    auth_password_hash_file=secret, auth_cookie_secure=False)


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def login(client, password=PASSWORD):
    return client.post("/api/v1/auth/connexion", json={"password": password})


def test_hash_is_salted_and_verifiable(encoded):
    assert encoded.startswith("scrypt$") and PASSWORD not in encoded
    assert auth.hash_password(PASSWORD) != encoded
    assert auth.verify_password(PASSWORD, encoded)
    assert not auth.verify_password(PASSWORD + "!", encoded)
    assert not auth.verify_password(PASSWORD, "invalide")
    with pytest.raises(ValueError):
        auth.hash_password("court")


def test_api_requires_session_but_health_stays_open(client):
    assert client.get("/api/v1/maison/equipements").status_code == 401
    assert client.get("/api/v1/auth/session").status_code == 401
    assert client.get("/health/ready").status_code == 200
    assert client.get("/version").status_code == 200
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_login_session_and_logout(client):
    response = login(client)
    assert response.status_code == 204
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie and "max-age=43200" in cookie
    assert client.get("/api/v1/maison/equipements").status_code == 200
    assert client.get("/api/v1/auth/session").json()["authenticated"]
    assert client.post("/api/v1/auth/deconnexion", json={}).status_code == 204
    assert client.get("/api/v1/maison/equipements").status_code == 401


def test_secure_cookie_by_default(settings):
    with TestClient(create_app(settings.model_copy(update={"auth_cookie_secure": True})),
                    base_url="https://testserver") as client:
        assert "secure" in login(client).headers["set-cookie"].lower()


def test_forged_or_revoked_token_rejected(client):
    client.cookies.set(auth.COOKIE, "jeton-invente")
    assert client.get("/api/v1/maison/equipements").status_code == 401
    client.cookies.clear()
    login(client)
    token = client.cookies.get(auth.COOKIE)
    client.post("/api/v1/auth/deconnexion", json={})
    client.cookies.clear()
    client.cookies.set(auth.COOKIE, token)
    assert client.get("/api/v1/maison/equipements").status_code == 401


def test_failures_are_limited(client):
    for _ in range(auth.MAX_FAILURES):
        assert login(client, "mauvais mot de passe").status_code == 401
    assert login(client).status_code == 429
    assert client.get("/api/v1/maison/equipements").status_code == 401


def test_success_resets_failure_count(client):
    for _ in range(auth.MAX_FAILURES - 1):
        login(client, "mauvais mot de passe")
    assert login(client).status_code == 204
    for _ in range(auth.MAX_FAILURES - 1):
        assert login(client, "mauvais mot de passe").status_code == 401
    assert login(client).status_code == 204


def test_post_requires_json(client):
    login(client)
    response = client.post("/api/v1/documents/recherche", content="query=x",
                           headers={"Content-Type": "application/x-www-form-urlencoded"})
    assert response.status_code == 415
    assert client.post("/api/v1/auth/connexion", data={"password": PASSWORD}).status_code == 415


@pytest.mark.parametrize("content", [None, "", "pas une empreinte", "scrypt$1$2$3"])
def test_missing_or_invalid_hash_file_answers_503(settings, tmp_path, content):
    path = tmp_path / "absent"
    if content is not None:
        path.write_text(content)
    with TestClient(create_app(settings.model_copy(update={"auth_password_hash_file": path}))) as client:
        assert login(client).status_code == 503
        assert client.get("/health/ready").status_code == 200


def test_hash_command_prints_only_the_hash(monkeypatch, capsys):
    answers = iter([PASSWORD, PASSWORD])
    monkeypatch.setattr("getpass.getpass", lambda prompt="": next(answers))
    assert auth.main([]) == 0
    output = capsys.readouterr().out.strip()
    assert auth.verify_password(PASSWORD, output) and PASSWORD not in output
    answers = iter([PASSWORD, "autre chose"])
    assert auth.main([]) == 1
