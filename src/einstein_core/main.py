"""Point d'entrée HTTP d'Einstein Core."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from einstein_core.ai.configuration import configure_provider
from einstein_core.ai.provider import AnswerProvider
from einstein_core.api.questions import router as questions_router
from einstein_core.maison.questions import QuestionService
from einstein_core.api.health import router as health_router
from einstein_core.api.maison import router as maison_router
from einstein_core.config import Settings, get_settings
from einstein_core.logging_config import configure_logging
from einstein_core.maison.inventory import load_inventory

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None, *, provider: AnswerProvider | None = None) -> FastAPI:
    """Construit une application dont le catalogue est chargé au démarrage."""

    settings = settings if settings is not None else get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.inventory = load_inventory(settings.maison_inventory_path)
        active_provider = (provider or configure_provider(settings)) if settings.ai_enabled else None
        app.state.questions = (
            QuestionService(
                active_provider, app.state.inventory,
                max_concurrency=settings.ai_max_concurrency,
                max_context_bytes=settings.ai_max_context_bytes,
            ) if active_provider is not None else None
        )
        logger.info(
            "Einstein Core démarre — environnement=%s version=%s",
            settings.environment,
            settings.version,
        )
        try:
            yield
        finally:
            app.state.questions = None
            if active_provider is not None:
                await active_provider.close()
            logger.info("Einstein Core s'arrête")

    app = FastAPI(title=settings.app_name, version=settings.version, lifespan=lifespan)
    app.include_router(health_router)
    app.include_router(maison_router)
    app.include_router(questions_router)

    @app.get("/version", tags=["metadata"])
    def version() -> dict[str, str]:
        return {
            "name": settings.app_name,
            "version": settings.version,
            "environment": settings.environment,
        }

    return app


configure_logging(get_settings().log_level)
app = create_app()
