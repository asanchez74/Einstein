"""Essai local Sign in with ChatGPT ; aucun appel d'inférence ou clé API."""

import argparse
import base64
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import secrets
import tempfile
import time
from urllib.parse import parse_qs, urlencode, urlsplit
import uuid
import webbrowser

import httpx2 as httpx
import jwt

ISSUER = "https://auth.openai.com"
RESOURCE = "https://api.openai.com/v1"
SCOPES = "openid profile email offline_access resource.invoke chatgpt.tokens.use.direct"


class LoginError(Exception):
    """Erreur locale sans code OAuth, jeton ou corps distant."""


def read_record(path: Path) -> dict:
    if not path.exists():
        return {}
    stat = path.lstat()
    if path.is_symlink() or stat.st_uid != os.getuid() or stat.st_mode & 0o077:
        raise LoginError("Permissions du fichier de connexion trop ouvertes")
    try:
        record = json.loads(path.read_text())
        if not isinstance(record, dict):
            raise ValueError
        return record
    except (OSError, ValueError):
        raise LoginError("Fichier de connexion illisible") from None


def save_record(path: Path, record: dict) -> None:
    """Écriture atomique 0600 dans le répertoire privé dédié."""
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".pending-")
    try:
        with os.fdopen(descriptor, "w") as file:
            json.dump(record, file)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


REGISTRATION_FIELDS = ("issuer", "subject", "client_id")


def retain_registration(directory: Path, record: dict) -> dict:
    """Conserve uniquement l'association validée, jamais les jetons."""
    registration = {field: record.get(field) for field in REGISTRATION_FIELDS}
    if (registration["issuer"] != ISSUER
            or not isinstance(registration["subject"], str) or not registration["subject"]
            or not isinstance(registration["client_id"], str)
            or not registration["client_id"].startswith("oaiapp_")):
        raise LoginError("Inscription locale invalide")
    saved = read_record(directory / "registration.json")
    if saved and saved != registration:
        raise LoginError("Inscription différente de celle conservée")
    save_record(directory / "registration.json", registration)
    return registration


def load_registration(directory: Path) -> dict:
    """Migre les anciennes sessions et permet un login sans jetons conservés."""
    credentials = read_record(directory / "credentials.json")
    if credentials:
        return retain_registration(directory, credentials)
    registration = read_record(directory / "registration.json")
    if registration:
        return retain_registration(directory, registration)
    return {}


def authorization_params(host_id: str, redirect: str, previous: dict) -> tuple[dict, str]:
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    client_id = previous.get("client_id", "dynamic_agent_client")
    params = {
        "client_id": client_id, "ext_agent_host_id": host_id,
        "response_type": "code", "redirect_uri": redirect, "scope": SCOPES,
        "resource": RESOURCE, "state": secrets.token_urlsafe(32),
        "nonce": secrets.token_urlsafe(32), "code_challenge_method": "S256",
        "code_challenge": challenge,
    }
    if client_id == "dynamic_agent_client":
        params["agent_name_hint"] = "Einstein"
    return params, verifier


def validate_callback(path: str, params: dict) -> tuple[str, str]:
    parsed = urlsplit(path)
    if parsed.path != "/auth/callback" or len(path) > 16384:
        raise LoginError("Callback invalide")
    try:
        values = parse_qs(parsed.query, max_num_fields=10)
    except ValueError:
        raise LoginError("Callback invalide") from None
    if any(len(value) != 1 for value in values.values()):
        raise LoginError("Callback ambigu")
    state = values.get("state", [""])[0]
    if not secrets.compare_digest(state, params["state"]):
        raise LoginError("État OAuth invalide")
    if "error" in values:
        raise LoginError("Connexion refusée ou abonnement non autorisé")
    client_id = values.get("client_id", [params["client_id"]])[0]
    if params["client_id"] != "dynamic_agent_client" and client_id != params["client_id"]:
        raise LoginError("Inscription différente de celle attendue")
    if not client_id.startswith("oaiapp_") or not values.get("code", [""])[0]:
        raise LoginError("Inscription incomplète")
    return values["code"][0], client_id


def validate_identity(tokens: dict, keys: dict, client_id: str, nonce: str, previous: dict) -> dict:
    stage = "jeton identité absent ou invalide"
    try:
        encoded = tokens["id_token"]
        header = jwt.get_unverified_header(encoded)
        stage = "clé de signature non reconnue"
        key = next(k for k in jwt.PyJWKSet.from_dict(keys).keys if k.key_id == header.get("kid"))
        stage = "signature ou attributs identité invalides"
        identity = jwt.decode(
            encoded, key.key, algorithms=["RS256", "ES256"], audience=client_id,
            issuer=ISSUER, leeway=5,
            options={"require": ["sub", "exp", "iat", "nonce"]},
        )
        audiences = identity.get("aud")
        if isinstance(audiences, list) and len(audiences) > 1 and identity.get("azp") != client_id:
            raise ValueError
        if identity.get("azp") is not None and identity["azp"] != client_id:
            raise ValueError
        stage = "identité ou nonce incohérent"
        if not isinstance(identity["sub"], str) or not identity["sub"]:
            raise ValueError
        if not secrets.compare_digest(identity["nonce"], nonce):
            raise ValueError
        if previous and identity["sub"] != previous.get("subject"):
            raise ValueError
        stage = "permission d’utilisation du forfait absente"
        scopes = tokens["scope"].split()
        if not {"resource.invoke", "chatgpt.tokens.use.direct"}.issubset(scopes):
            raise ValueError
        stage = "jetons d’accès ou de renouvellement absents"
        for field in ("access_token", "refresh_token"):
            if not isinstance(tokens[field], str) or not tokens[field]:
                raise ValueError
        stage = "type de jeton incompatible"
        if str(tokens.get("token_type", "")).lower() != "bearer":
            raise ValueError
        return identity
    except jwt.PyJWTError as exc:
        # Nom de classe uniquement, jamais le contenu du jeton ou de l'erreur.
        raise LoginError(f"Validation identité refusée ({type(exc).__name__})") from None
    except (ValueError, TypeError, KeyError, StopIteration, AttributeError):
        raise LoginError(f"Connexion non validée : {stage}") from None


def run(directory: Path, timeout: int) -> None:
    directory = directory.expanduser()
    if directory.is_symlink():
        raise LoginError("Répertoire de connexion invalide")
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if directory.stat().st_uid != os.getuid() or directory.stat().st_mode & 0o077:
        raise LoginError("Le répertoire de connexion doit appartenir à l'utilisateur et être en mode 0700")
    previous = load_registration(directory)
    host = read_record(directory / "host.json")
    if not host:
        host = {"ext_agent_host_id": f"urn:uuid:{uuid.uuid4()}"}
        save_record(directory / "host.json", host)

    result = {}

    class Callback(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # Ne jamais journaliser les codes OAuth dans les URLs.

        def do_GET(self):
            if urlsplit(self.path).path != "/auth/callback":
                self.send_error(404)
                return
            try:
                result["callback"] = validate_callback(self.path, params)
                message = "Connexion reçue. Vous pouvez revenir au terminal Einstein."
                status = 200
            except LoginError as exc:
                result["error"] = exc
                message, status = "Connexion non validée. Revenez au terminal Einstein.", 400
            self.send_response(status)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(message.encode())

    # HTTPServer gère uniquement la boucle locale du Mac, jamais le LAN.
    with HTTPServer(("127.0.0.1", 0), Callback) as server:
        server.timeout = 1
        redirect = f"http://127.0.0.1:{server.server_port}/auth/callback"
        params, verifier = authorization_params(host["ext_agent_host_id"], redirect, previous)
        print("Continue with ChatGPT — ouverture du navigateur. Aucun appel d'inférence.", flush=True)
        if not webbrowser.open(ISSUER + "/api/accounts/authorize?" + urlencode(params)):
            raise LoginError("Impossible d'ouvrir le navigateur")
        deadline = time.monotonic() + timeout
        while not result and time.monotonic() < deadline:
            server.handle_request()
        if "error" in result:
            raise result["error"]
        if "callback" not in result:
            raise LoginError("Connexion expirée ; relancer une tentative")
    code, client_id = result["callback"]
    try:
        with httpx.Client(timeout=20, trust_env=False) as client:
            response = client.post(ISSUER + "/api/accounts/oauth/token", data={
                "grant_type": "authorization_code", "client_id": client_id,
                "code": code, "code_verifier": verifier, "redirect_uri": redirect,
                "resource": RESOURCE,
            })
            response.raise_for_status()
            tokens = response.json()
            jwks = client.get(ISSUER + "/.well-known/jwks.json")
            jwks.raise_for_status()
            identity = validate_identity(tokens, jwks.json(), client_id, params["nonce"], previous)
            retain_registration(directory, {
                "issuer": ISSUER, "subject": identity["sub"], "client_id": client_id,
            })
            save_record(directory / "credentials.json", {
                "issuer": ISSUER, "subject": identity["sub"], "client_id": client_id,
                "ext_agent_host_id": host["ext_agent_host_id"],
                "access_token": tokens["access_token"], "refresh_token": tokens["refresh_token"],
                "id_token": tokens["id_token"], "scope": tokens["scope"],
                "expires_in": tokens.get("expires_in"), "saved_at": time.time(),
            })
            models = client.get(RESOURCE + "/models", headers={
                "Authorization": "Bearer " + tokens["access_token"],
            })
            models.raise_for_status()
            visible = [m["slug"] for m in models.json()["models"] if m.get("visibility") == "list"]
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        raise LoginError("Échange OAuth ou catalogue de modèles refusé ; aucun appel d'inférence effectué") from None
    print("Connexion et permission du forfait validées. Aucun jeton affiché.")
    print("Modèles accessibles : " + ", ".join(visible))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Essai local du forfait ChatGPT pour Einstein")
    parser.add_argument("--credentials-dir", type=Path, default=Path.home() / ".config/einstein/chatgpt")
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args(argv)
    if not 1 <= args.timeout <= 600:
        parser.error("Le délai doit être compris entre 1 et 600 secondes")
    try:
        run(args.credentials_dir, args.timeout)
    except LoginError as exc:
        print(f"Connexion ChatGPT non terminée : {exc}.")
        return 1
    except OSError:
        print("Connexion ChatGPT non terminée : erreur locale, aucun appel d'inférence.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
