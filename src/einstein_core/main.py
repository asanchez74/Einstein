"""Point d'entrée HTTP d'Einstein Core."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import logging
from pathlib import Path
import threading

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from einstein_core.ai.configuration import configure_provider
from einstein_core.ai.provider import AnswerProvider
from einstein_core.api.auth import router as auth_router
from einstein_core.api.questions import router as questions_router
from einstein_core.auth import COOKIE, FailureLimiter, SessionStore
from einstein_core.api.documents import router as documents_router
from einstein_core.documents.search import build_index
from einstein_core.maison.questions import QuestionService
from einstein_core.api.health import router as health_router
from einstein_core.api.maison import router as maison_router
from einstein_core.config import Settings, get_settings
from einstein_core.logging_config import configure_logging
from einstein_core.maison.inventory import load_inventory

logger = logging.getLogger(__name__)

UI_DIR = Path(__file__).parent / "ui" / "static"
# Page sans ressource externe ni script en ligne (ADR-0011).
UI_POLICY = ("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
             "connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'")


def create_app(settings: Settings | None = None, *, provider: AnswerProvider | None = None) -> FastAPI:
    """Construit une application dont le catalogue est chargé au démarrage."""

    settings = settings if settings is not None else get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.inventory = load_inventory(settings.maison_inventory_path)
        app.state.documents = None
        app.state.documents_indexing = False
        stop_indexing = threading.Event()
        indexing_task = None

        async def index_documents(extractor) -> None:
            # En arrière-plan : le Core répond pendant l'extraction ; aucun nom ni contenu journalisé.
            try:
                ocr = None
                if settings.documents_ocr_cache_path is not None:
                    from einstein_core.documents.ocr import cached_ocr
                    ocr = cached_ocr(settings.documents_path, settings.documents_ocr_cache_path)
                index = await asyncio.to_thread(
                    build_index, settings.documents_path, extractor=extractor,
                    budget_seconds=settings.documents_index_budget_seconds, stop=stop_indexing, ocr=ocr,
                )
                app.state.documents = index
                logger.info("Index documentaire prêt — fichiers=%d écartés=%d partiel=%s",
                            index.indexed_files, index.skipped_files, index.partial)
            except (OSError, ValueError):
                logger.warning("Recherche documentaire indisponible")
            finally:
                app.state.documents_indexing = False

        if settings.documents_enabled:
            try:
                extractor = None
                if settings.documents_mode == "openai":
                    from einstein_core.documents.ingest import cached_extractor
                    if settings.documents_cache_path is None or not settings.ai_model:
                        raise ValueError("Cache documentaire et modèle requis")
                    extractor = cached_extractor(settings.documents_path, settings.documents_cache_path, settings.ai_model)
                app.state.documents_indexing = True
                indexing_task = asyncio.create_task(index_documents(extractor))
            except (OSError, ValueError):
                logger.warning("Recherche documentaire indisponible")
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
            stop_indexing.set()
            if indexing_task is not None:
                await indexing_task
            app.state.questions = None
            if active_provider is not None:
                await active_provider.close()
            logger.info("Einstein Core s'arrête")

    # Documentation interactive coupée quand l'authentification protège l'API.
    docs = {"docs_url": None, "redoc_url": None, "openapi_url": None} if settings.auth_enabled else {}
    app = FastAPI(title=settings.app_name, version=settings.version, lifespan=lifespan, **docs)
    app.state.settings = settings
    app.state.sessions = SessionStore(settings.auth_session_hours * 3600)
    app.state.login_failures = FailureLimiter()

    @app.middleware("http")
    async def require_session(request: Request, call_next):
        path = request.url.path
        if settings.auth_enabled and path.startswith("/api/"):
            if request.method == "POST" and request.headers.get("content-type", "").split(";")[0].strip() != "application/json":
                # Avec SameSite=Strict, écarte les formulaires inter-sites.
                return JSONResponse({"detail": "Contenu JSON requis"}, status_code=415)
            public = path in {"/api/v1/auth/connexion", "/api/v1/auth/deconnexion"}
            if not public and app.state.sessions.expiry(request.cookies.get(COOKIE)) is None:
                return JSONResponse({"detail": "Authentification requise"}, status_code=401)
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        if path == "/" or path.startswith("/ui/"):
            response.headers["Content-Security-Policy"] = UI_POLICY
            response.headers["X-Frame-Options"] = "DENY"
        return response

    @app.get("/", include_in_schema=False)
    def interface() -> FileResponse:
        return FileResponse(UI_DIR / "index.html", headers={"Cache-Control": "no-cache"})

    app.mount("/ui", StaticFiles(directory=UI_DIR), name="ui")

    app.include_router(auth_router)
    app.include_router(health_router)
    app.include_router(maison_router)
    app.include_router(questions_router)
    app.include_router(documents_router)

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
