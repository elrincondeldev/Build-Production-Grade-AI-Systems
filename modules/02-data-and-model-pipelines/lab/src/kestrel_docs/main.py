"""App factory. Run with:

    uv run uvicorn kestrel_docs.main:create_app --factory --port 8000
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from kestrel_docs.api.routes import router
from kestrel_docs.config import Settings, get_settings
from kestrel_docs.service import build_services


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Build the index once at startup. Until this finishes, /readyz returns 503,
        # so a load balancer will not send traffic to a half-ready instance.
        app.state.services = build_services(settings)
        yield

    app = FastAPI(title="Kestrel docs-assistant (Module 2)", version="0.2.0", lifespan=lifespan)
    app.include_router(router)
    return app
