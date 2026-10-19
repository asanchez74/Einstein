"""Interface web : page servie sans ressource externe, en-têtes de sécurité, session."""

import re

from fastapi.testclient import TestClient

from einstein_core import auth
from einstein_core.config import Settings
from einstein_core.main import UI_DIR, create_app


def app_settings(tmp_path, **overrides):
    inventory = tmp_path / "inventory.json"
    inventory.write_text("[]")
    return Settings(maison_inventory_path=inventory, **overrides)


def test_page_and_assets_with_security_headers(tmp_path):
    with TestClient(create_app(app_settings(tmp_path))) as client:
        page = client.get("/")
        assert page.status_code == 200 and "text/html" in page.headers["content-type"]
        policy = page.headers["content-security-policy"]
        assert "default-src 'self'" in policy and "frame-ancestors 'none'" in policy
        assert page.headers["x-frame-options"] == "DENY"
        assert page.headers["referrer-policy"] == "no-referrer"
        for asset, kind in (("/ui/app.js", "javascript"), ("/ui/app.css", "text/css")):
            response = client.get(asset)
            assert response.status_code == 200 and kind in response.headers["content-type"]
            assert response.headers["x-content-type-options"] == "nosniff"
        assert client.get("/ui/../main.py").status_code == 404


def test_ui_has_no_external_resources_or_inline_html_injection():
    html = (UI_DIR / "index.html").read_text()
    script = (UI_DIR / "app.js").read_text()
    assert not re.search(r"(src|href)=\"(https?:)?//", html)
    assert "<script>" not in html and "style=" not in html
    assert "innerHTML" not in script and "insertAdjacentHTML" not in script


def test_session_reports_whether_login_is_required(tmp_path):
    with TestClient(create_app(app_settings(tmp_path))) as client:
        assert client.get("/api/v1/auth/session").json() == {
            "authenticated": True, "required": False, "expires_at": None}
    secret = tmp_path / "hash"
    secret.write_text(auth.hash_password("correct horse battery staple"))
    settings = app_settings(tmp_path, auth_enabled=True, auth_password_hash_file=secret, auth_cookie_secure=False)
    with TestClient(create_app(settings)) as client:
        assert client.get("/").status_code == 200
        assert client.get("/api/v1/auth/session").status_code == 401
        client.post("/api/v1/auth/connexion", json={"password": "correct horse battery staple"})
        session = client.get("/api/v1/auth/session").json()
        assert session["required"] and session["expires_at"]
