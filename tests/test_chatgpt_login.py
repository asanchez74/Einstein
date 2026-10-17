"""Validation du parcours Plus sans authentification distante."""

import base64
import hashlib
import json
import os
import time
from urllib.parse import urlencode

from cryptography.hazmat.primitives.asymmetric import rsa
import jwt
import pytest

from einstein_core.ai.chatgpt_login import (
    ISSUER, LoginError, authorization_params, read_record, save_record,
    validate_callback, validate_identity,
)


def test_pkce_and_first_registration():
    params, verifier = authorization_params("urn:uuid:test", "http://127.0.0.1:1234/auth/callback", {})
    assert params["client_id"] == "dynamic_agent_client"
    assert params["agent_name_hint"] == "Einstein"
    assert params["code_challenge"] == base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    assert "chatgpt.tokens.use.direct" in params["scope"]
    other, _ = authorization_params("urn:uuid:test", params["redirect_uri"], {"client_id": "oaiapp_saved"})
    assert "agent_name_hint" not in other
    assert other["client_id"] == "oaiapp_saved"
    assert other["state"] != params["state"] and other["nonce"] != params["nonce"]


@pytest.mark.parametrize("query", [
    {"state": "wrong", "code": "private", "client_id": "oaiapp_new"},
    {"state": "expected", "error": "access_denied"},
    {"state": "expected", "code": "private"},
    {"state": "expected", "code": "private", "client_id": "dynamic_agent_client"},
])
def test_invalid_callback(query):
    with pytest.raises(LoginError) as exc:
        validate_callback("/auth/callback?" + urlencode(query), {"state": "expected", "client_id": "dynamic_agent_client"})
    assert "private" not in str(exc.value)


def test_callback_registration_and_returning_identity():
    path = "/auth/callback?" + urlencode({"state": "expected", "code": "private", "client_id": "oaiapp_new"})
    assert validate_callback(path, {"state": "expected", "client_id": "dynamic_agent_client"}) == ("private", "oaiapp_new")
    with pytest.raises(LoginError):
        validate_callback(path, {"state": "expected", "client_id": "oaiapp_other"})
    with pytest.raises(LoginError):
        validate_callback(path + "&state=expected", {"state": "expected", "client_id": "dynamic_agent_client"})


@pytest.fixture
def signed_tokens():
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    key = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private.public_key()))
    key["kid"] = "test"
    claims = {"sub": "account", "iss": ISSUER, "aud": "oaiapp_test", "nonce": "nonce",
              "iat": int(time.time()), "exp": int(time.time()) + 60}
    def make(**changes):
        return {
            "id_token": jwt.encode({**claims, **changes}, private, algorithm="RS256", headers={"kid": "test"}),
            "scope": "resource.invoke chatgpt.tokens.use.direct", "access_token": "fake-access",
            "refresh_token": "fake-refresh", "token_type": "Bearer",
        }
    return make, {"keys": [key]}


def test_verified_identity_and_scopes(signed_tokens):
    make, keys = signed_tokens
    assert validate_identity(make(), keys, "oaiapp_test", "nonce", {})["sub"] == "account"
    tokens = make()
    tokens["scope"] = "openid"
    with pytest.raises(LoginError):
        validate_identity(tokens, keys, "oaiapp_test", "nonce", {})


@pytest.mark.parametrize("changes", [{"iss": "wrong"}, {"aud": "wrong"}, {"nonce": "wrong"},
                                       {"exp": 1}, {"sub": ""}])
def test_invalid_identity(signed_tokens, changes):
    make, keys = signed_tokens
    with pytest.raises(LoginError):
        validate_identity(make(**changes), keys, "oaiapp_test", "nonce", {})


def test_account_switch_and_invalid_signature(signed_tokens):
    make, keys = signed_tokens
    with pytest.raises(LoginError):
        validate_identity(make(), keys, "oaiapp_test", "nonce", {"subject": "another"})
    tokens = make()
    header, payload, signature = tokens["id_token"].split(".")
    replacement = "A" if signature[0] != "A" else "B"
    tokens["id_token"] = f"{header}.{payload}.{replacement}{signature[1:]}"
    with pytest.raises(LoginError):
        validate_identity(tokens, keys, "oaiapp_test", "nonce", {})


def test_private_atomic_storage(tmp_path):
    path = tmp_path / "credentials.json"
    save_record(path, {"access_token": "private"})
    assert path.stat().st_mode & 0o777 == 0o600
    assert read_record(path)["access_token"] == "private"
    assert list(tmp_path.iterdir()) == [path]
    path.chmod(0o644)
    with pytest.raises(LoginError):
        read_record(path)


def test_symlink_credentials_rejected(tmp_path):
    path = tmp_path / "real.json"
    save_record(path, {})
    link = tmp_path / "linked.json"
    link.symlink_to(path)
    with pytest.raises(LoginError):
        read_record(link)


def test_multiple_audiences_require_authorized_party(signed_tokens):
    make, keys = signed_tokens
    tokens = make(aud=["oaiapp_test", "other"], azp="oaiapp_test")
    assert validate_identity(tokens, keys, "oaiapp_test", "nonce", {})["sub"] == "account"
    with pytest.raises(LoginError):
        validate_identity(make(aud=["oaiapp_test", "other"]), keys, "oaiapp_test", "nonce", {})
    with pytest.raises(LoginError):
        validate_identity(make(azp="other"), keys, "oaiapp_test", "nonce", {})
