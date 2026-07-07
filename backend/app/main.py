from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.assets import router as assets_router
from app.api.dossiers import router as dossiers_router
from app.api.events import router as events_router
from app.api.health import router as health_router
from app.api.sources import router as sources_router
from app.config import get_settings
from app.obs import TimingMiddleware, configure_logging


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()
    app = FastAPI(title="Operational Context Engine", version="0.1.0")
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
    app.include_router(sources_router)
    app.include_router(assets_router)
    return app


app = create_app()
