"""Session Plus : renouvellement atomique sérialisé, sans repli API."""

import fcntl
import math
import os
from pathlib import Path
import time

import httpx2 as httpx

from einstein_core.ai.chatgpt_login import ISSUER, RESOURCE, LoginError, load_registration, read_record, retain_registration, save_record
from einstein_core.ai.provider import ProviderError


def access_token(path: Path) -> str:
    """Relit le fichier sous verrou, renouvelle si l'expiration est proche."""
    parent = path.parent
    try:
        stat = parent.stat()
        if parent.is_symlink() or stat.st_uid != os.getuid() or stat.st_mode & 0o077:
            raise LoginError("Dossier de session non privé")
        descriptor = os.open(parent / ".session.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, "w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            record = read_record(path)
            if record.get("issuer") != ISSUER or not record.get("subject"):
                raise LoginError("Identité absente")
            if not str(record.get("client_id", "")).startswith("oaiapp_"):
                raise LoginError("Client absent")
            scopes = set(record.get("scope", "").split())
            if not {"chatgpt.tokens.use.direct", "resource.invoke"}.issubset(scopes):
                raise LoginError("Forfait non autorisé")
            token = record.get("access_token")
            if not isinstance(token, str) or not token:
                raise LoginError("Session absente")
            expires = float(record.get("expires_in", 0))
            saved = float(record.get("saved_at", 0))
            if not math.isfinite(expires + saved):
                raise LoginError("Expiration invalide")
            if saved + expires > time.time() + 60:
                return token
            refresh = record.get("refresh_token")
            if not isinstance(refresh, str) or not refresh:
                raise LoginError("Reconnexion requise")
            with httpx.Client(timeout=15, trust_env=False) as client:
                response = client.post(ISSUER + "/api/accounts/oauth/token", data={
                    "grant_type": "refresh_token", "client_id": record["client_id"],
                    "refresh_token": refresh, "resource": RESOURCE,
                })
                response.raise_for_status()
                tokens = response.json()
            if str(tokens.get("token_type", "")).lower() != "bearer":
                raise LoginError("Type de session invalide")
            for field in ("access_token", "refresh_token"):
                if not isinstance(tokens.get(field), str) or not tokens[field]:
                    raise LoginError("Renouvellement incomplet")
            scope = tokens.get("scope", record["scope"])
            if not {"chatgpt.tokens.use.direct", "resource.invoke"}.issubset(scope.split()):
                raise LoginError("Permission révoquée")
            lifetime = float(tokens["expires_in"])
            if not math.isfinite(lifetime) or lifetime <= 0:
                raise LoginError("Expiration invalide")
            updated = {**record, "access_token": tokens["access_token"],
                       "refresh_token": tokens["refresh_token"], "scope": scope,
                       "expires_in": lifetime, "saved_at": time.time()}
            save_record(path, updated)
            return updated["access_token"]
    except (LoginError, OSError, httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError):
        raise ProviderError("Session ChatGPT indisponible ; reconnecter le compte si nécessaire") from None


def session_status(path: Path, now: float | None = None) -> str:
    """Résumé lisible sans jeton ni appel réseau, pour planifier le contrôle de refresh."""
    from datetime import datetime

    record = read_record(path)
    if not record:
        return "Aucune session enregistrée."
    try:
        saved = float(record["saved_at"])
        expires = saved + float(record["expires_in"])
        if not math.isfinite(expires):
            raise ValueError
    except (KeyError, TypeError, ValueError):
        return "Session présente ; expiration inconnue ou invalide."
    remaining = round((expires - (time.time() if now is None else now)) / 60)
    renewable = "oui" if isinstance(record.get("refresh_token"), str) and record["refresh_token"] else "non"
    state = (f"valide encore {remaining} min" if remaining > 1 else
             f"à renouveler (échéance dépassée de {max(-remaining, 0)} min)")
    return (f"Session présente ; jeton d'accès {state}. "
            f"Expiration : {datetime.fromtimestamp(expires).astimezone().isoformat(timespec='seconds')}. "
            f"Dernier enregistrement : {datetime.fromtimestamp(saved).astimezone().isoformat(timespec='seconds')}. "
            f"Renouvelable : {renewable}.")


def prepare_host(directory: Path, source: Path | None = None) -> None:
    """Initialise l'hôte distant ; importe au plus une session sans écraser."""
    import uuid

    if directory.is_symlink():
        raise LoginError("Répertoire de session invalide")
    directory.mkdir(parents=True, mode=0o700, exist_ok=True)
    stat = directory.stat()
    if stat.st_uid != os.getuid() or stat.st_mode & 0o077:
        raise LoginError("Le dossier doit appartenir à l'utilisateur et être privé (0700)")
    host = read_record(directory / "host.json")
    if not host:
        host = {"ext_agent_host_id": f"urn:uuid:{uuid.uuid4()}"}
        save_record(directory / "host.json", host)
    load_registration(directory)
    if source is None:
        return
    target = directory / "credentials.json"
    if target.exists() or target.is_symlink():
        raise LoginError("Une session existe déjà ; aucun remplacement automatique")
    record = read_record(source)
    required = ("subject", "client_id", "access_token", "refresh_token", "scope")
    if record.get("issuer") != ISSUER or any(not isinstance(record.get(k), str) or not record[k] for k in required):
        raise LoginError("Session source incomplète")
    if not record["client_id"].startswith("oaiapp_") or not {
        "resource.invoke", "chatgpt.tokens.use.direct",
    }.issubset(record["scope"].split()):
        raise LoginError("Session source non autorisée pour le forfait")
    retain_registration(directory, record)
    # Ne jamais importer l'identifiant d'hôte du Mac sur le NAS.
    save_record(target, {**record, "ext_agent_host_id": host["ext_agent_host_id"]})


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Préparer un hôte Einstein pour une session Plus")
    parser.add_argument("--directory", type=Path, required=True)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--import-from", dest="source", type=Path)
    action.add_argument("--status", action="store_true", help="Afficher l'expiration sans jeton ni réseau")
    args = parser.parse_args(argv)
    if args.status:
        try:
            print(session_status(args.directory / "credentials.json"))
        except (LoginError, OSError):
            print("État de session illisible ; vérifier permissions et UID.")
            return 1
        return 0
    try:
        prepare_host(args.directory, args.source)
    except (LoginError, OSError):
        print("Préparation de session refusée ; vérifier permissions et présence d'une session existante.")
        return 1
    print("Session importée sans afficher de jeton." if args.source else "Identifiant d'hôte prêt.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
