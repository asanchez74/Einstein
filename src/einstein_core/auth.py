"""Authentification à compte unique : empreinte scrypt, sessions en mémoire (ADR-0011)."""

import base64
from collections import deque
import hashlib
import hmac
from pathlib import Path
import secrets
import threading
import time

SCHEME = "scrypt"
N, R, P = 2**15, 8, 1
# scrypt réserve 128 * R * N octets (32 MiB) ; marge pour la bibliothèque.
MAXMEM = 64 * 1024 * 1024
MIN_LENGTH = 12
MAX_LENGTH = 1024
MAX_FAILURES = 5
FAILURE_WINDOW = 15 * 60
COOKIE = "einstein_session"


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def hash_password(password: str) -> str:
    if not MIN_LENGTH <= len(password) <= MAX_LENGTH:
        raise ValueError(f"Mot de passe de {MIN_LENGTH} à {MAX_LENGTH} caractères requis")
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=N, r=R, p=P, maxmem=MAXMEM, dklen=32)
    return f"{SCHEME}${N}${R}${P}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, n, r, p, salt, expected = encoded.split("$")
        if scheme != SCHEME or len(password) > MAX_LENGTH:
            return False
        digest = hashlib.scrypt(password.encode(), salt=_unb64(salt), n=int(n), r=int(r), p=int(p),
                                maxmem=MAXMEM, dklen=32)
        return hmac.compare_digest(digest, _unb64(expected))
    except (ValueError, TypeError):
        return False


def load_hash(path: Path | None) -> str | None:
    """Empreinte lue à chaque connexion : un remplacement du fichier ne demande pas de redémarrage."""
    if path is None:
        return None
    try:
        with path.open("rb") as file:
            raw = file.read(1025)
        text = raw.decode("ascii").strip()
    except (OSError, UnicodeError):
        return None
    if len(raw) > 1024 or len(text.split("$")) != 6 or not text.startswith(SCHEME + "$"):
        return None
    return text


class SessionStore:
    """Jetons aléatoires conservés sous forme d'empreinte ; perdus au redémarrage."""

    def __init__(self, lifetime_seconds: int) -> None:
        self._lifetime = lifetime_seconds
        self._sessions: dict[str, float] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _key(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def create(self) -> str:
        token = secrets.token_urlsafe(32)
        now = time.time()
        with self._lock:
            self._sessions = {key: expiry for key, expiry in self._sessions.items() if expiry > now}
            self._sessions[self._key(token)] = now + self._lifetime
        return token

    def expiry(self, token: str | None) -> float | None:
        if not token or len(token) > 128:
            return None
        with self._lock:
            expiry = self._sessions.get(self._key(token))
        return expiry if expiry is not None and expiry > time.time() else None

    def revoke(self, token: str | None) -> None:
        if token:
            with self._lock:
                self._sessions.pop(self._key(token), None)


class FailureLimiter:
    """Compte unique : la limite est globale, pas par adresse."""

    def __init__(self, limit: int = MAX_FAILURES, window: int = FAILURE_WINDOW) -> None:
        self._limit, self._window = limit, window
        self._failures: deque[float] = deque()
        self._lock = threading.Lock()

    def _trim(self, now: float) -> None:
        while self._failures and self._failures[0] <= now - self._window:
            self._failures.popleft()

    def blocked(self) -> bool:
        with self._lock:
            self._trim(time.monotonic())
            return len(self._failures) >= self._limit

    def record(self) -> None:
        with self._lock:
            now = time.monotonic()
            self._trim(now)
            self._failures.append(now)

    def reset(self) -> None:
        with self._lock:
            self._failures.clear()


def main(argv: list[str] | None = None) -> int:
    import argparse
    from getpass import getpass
    import sys

    parser = argparse.ArgumentParser(description="Générer l'empreinte du mot de passe Einstein")
    parser.parse_args(argv)
    # Invites sur le terminal ; seule l'empreinte sort sur stdout, pour une redirection vers le fichier secret.
    password = getpass("Mot de passe Einstein : ")
    if password != getpass("Confirmer : "):
        print("Les deux saisies diffèrent.", file=sys.stderr)
        return 1
    try:
        print(hash_password(password))
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
