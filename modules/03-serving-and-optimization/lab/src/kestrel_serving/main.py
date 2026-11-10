"""App factory. Run with:  uv run uvicorn kestrel_serving.main:create_app --factory --port 8000"""

from __future__ import annotations

import time
import uuid

import structlog
from fastapi import FastAPI, Request

from kestrel_serving.adapters.cache import ExactCache, SemanticCache
from kestrel_serving.adapters.embeddings import build_embedder
from kestrel_serving.adapters.llm import LLMClient, build_llm
from kestrel_serving.api.routes import router
from kestrel_serving.config import Settings, get_settings
from kestrel_serving.domain.answering import AnswerService
from kestrel_serving.domain.retrieval import Retriever, load_handbook

log = structlog.get_logger()


def build_service(settings: Settings, llm: LLMClient | None = None) -> AnswerService:
    embedder = build_embedder(settings.embeddings_provider)
    retriever = Retriever(load_handbook(settings.data_dir / "handbook"), embedder)
    llm = llm or build_llm(settings)
    exact = ExactCache(settings.cache_ttl_s, settings.cache_max_entries) if settings.cache_exact_enabled else None
    semantic = (
        SemanticCache(embedder, settings.cache_semantic_threshold, settings.cache_ttl_s, settings.cache_max_entries)
        if settings.cache_semantic_enabled
        else None
    )
    model_name = getattr(llm, "model", settings.llm_provider)
    return AnswerService(
        retriever, llm, exact, semantic, settings.retrieval_top_k, cache_scope=f"{settings.prompt_version}|{model_name}"
    )


def create_app(settings: Settings | None = None, llm: LLMClient | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title="Kestrel docs-assistant (Module 3)", version="0.3.0")
    app.state.service = build_service(settings, llm)
    app.include_router(router)

    @app.middleware("http")
    async def timing(request: Request, call_next):  # type: ignore[no-untyped-def]
        request_id = request.headers.get("x-request-id", uuid.uuid4().hex[:12])
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["x-request-id"] = request_id
        # Server-Timing shows up in browser dev tools and is easy to scrape in load tests.
        response.headers["server-timing"] = f"app;dur={elapsed_ms:.1f}"
        log.info("request", path=request.url.path, status=response.status_code, ms=round(elapsed_ms, 1), request_id=request_id)
        return response

    return app
