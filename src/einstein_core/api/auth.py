"""Connexion, déconnexion et état de session (ADR-0011)."""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from einstein_core.auth import COOKIE, MAX_LENGTH, load_hash, verify_password

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid")
    password: str = Field(min_length=1, max_length=MAX_LENGTH)


class SessionInfo(BaseModel):
    authenticated: bool
    expires_at: str


@router.post("/connexion", status_code=204)
def login(payload: Credentials, request: Request, response: Response) -> None:
    state = request.app.state
    encoded = load_hash(state.settings.auth_password_hash_file)
    if encoded is None:
        raise HTTPException(status_code=503, detail="Authentification non configurée")
    if state.login_failures.blocked():
        raise HTTPException(status_code=429, detail="Trop d'échecs ; réessayer dans quinze minutes")
    if not verify_password(payload.password, encoded):
        state.login_failures.record()
        raise HTTPException(status_code=401, detail="Mot de passe incorrect")
    state.login_failures.reset()
    token = state.sessions.create()
    response.set_cookie(
        COOKIE, token, max_age=state.settings.auth_session_hours * 3600, path="/",
        secure=state.settings.auth_cookie_secure, httponly=True, samesite="strict",
    )


@router.post("/deconnexion", status_code=204)
def logout(request: Request, response: Response) -> None:
    request.app.state.sessions.revoke(request.cookies.get(COOKIE))
    response.delete_cookie(COOKIE, path="/", secure=request.app.state.settings.auth_cookie_secure,
                           httponly=True, samesite="strict")


@router.get("/session", response_model=SessionInfo)
def session(request: Request) -> SessionInfo:
    # Le middleware a déjà vérifié la session ; cette route en donne l'échéance.
    expiry = request.app.state.sessions.expiry(request.cookies.get(COOKIE))
    if expiry is None:
        raise HTTPException(status_code=401, detail="Authentification requise")
    return SessionInfo(authenticated=True,
                       expires_at=datetime.fromtimestamp(expiry, timezone.utc).isoformat(timespec="seconds"))
