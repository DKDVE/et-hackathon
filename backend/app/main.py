import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.assets import router as assets_router
from app.api.config import router as config_router
from app.api.dossiers import router as dossiers_router
from app.api.events import router as events_router
from app.api.health import router as health_router
from app.api.limiter import limiter
from app.api.ops import router as ops_router
from app.api.sources import router as sources_router
from app.config import get_settings
from app.llm.embeddings import prewarm_embedder
from app.obs import TimingMiddleware, configure_logging

logger = logging.getLogger("oce")

_prewarm_started = False
_prewarm_lock = threading.Lock()


def _ensure_prewarm() -> None:
    global _prewarm_started
    with _prewarm_lock:
        if _prewarm_started:
            return
        _prewarm_started = True
        logger.info("Embedder warm-up starting")
        threading.Thread(
            target=prewarm_embedder,
            name="embedder-prewarm",
            daemon=True,
        ).start()


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    _ensure_prewarm()
    yield


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()
    app = FastAPI(title="Operational Context Engine", version="0.1.0", lifespan=_lifespan)
    app.state.limiter = limiter

    @app.exception_handler(RateLimitExceeded)
    async def _chat_rate_limit(_request: Request, _exc: RateLimitExceeded) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content={"message": "Rate limit reached — try again in a moment."},
        )

    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(TimingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(events_router)
    app.include_router(dossiers_router)
    app.include_router(config_router)
    app.include_router(sources_router)
    app.include_router(assets_router)
    app.include_router(ops_router)
    return app


app = create_app()
_ensure_prewarm()
