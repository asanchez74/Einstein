"""Point d'entrée HTTP d'Einstein Core."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from einstein_core.api.health import router as health_router
from einstein_core.config import get_settings
from einstein_core.logging_config import configure_logging

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Journalise le cycle de vie du service."""

    logger.info(
        "Einstein Core démarre — environnement=%s version=%s",
        settings.environment,
        settings.version,
    )
    yield
    logger.info("Einstein Core s'arrête")


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    lifespan=lifespan,
)

app.include_router(health_router)


@app.get("/version", tags=["metadata"])
def version() -> dict[str, str]:
    """Expose la version et l'environnement du service."""

    return {
        "name": settings.app_name,
        "version": settings.version,
        "environment": settings.environment,
    }
