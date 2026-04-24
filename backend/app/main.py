from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router
from app.container import AppContainer
from app.core.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    container = AppContainer(resolved_settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        container.initialize()
        container.start_background_services()
        try:
            yield
        finally:
            container.stop_background_services()

    app = FastAPI(title=resolved_settings.app_name, lifespan=lifespan)
    app.state.container = container

    if resolved_settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=resolved_settings.cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["*"],
        )

    app.include_router(api_router, prefix=resolved_settings.api_prefix)
    return app


app = create_app()
