"""Endpoints de santé."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    """Réponse normalisée d'un contrôle de santé."""

    status: Literal["ok", "ready"]


@router.get("/live", response_model=HealthResponse)
def liveness() -> HealthResponse:
    """Confirme que le processus HTTP fonctionne."""

    return HealthResponse(status="ok")


@router.get("/ready", response_model=HealthResponse)
def readiness() -> HealthResponse:
    """Confirme que le service est prêt à recevoir des requêtes."""

    return HealthResponse(status="ready")
