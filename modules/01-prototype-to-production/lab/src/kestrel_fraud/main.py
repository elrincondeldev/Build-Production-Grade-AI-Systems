"""Application factory (📖 lesson 1.4).

``create_app()`` wires the layers together: config → adapters → domain → API.
Nothing here contains business logic; it is the composition root.

Run locally:
    uv run uvicorn kestrel_fraud.main:create_app --factory --port 8001
"""

from __future__ import annotations

import random
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from . import __version__
from .adapters.artifacts import ArtifactError, load_artifact
from .adapters.enrichment import HttpFeatureStore
from .adapters.llm import LLMClient, build_llm
from .adapters.recent_scores import LRUStore
from .adapters.retry import RetryBudget, RetryPolicy
from .api.middleware import RequestIdMiddleware
from .api.routes import router
from .config import Settings, get_settings
from .domain.scoring import DecisionPolicy, FraudScorer
from .domain.service import ScoringService
from .logging import configure_logging, get_logger


def create_app(
    settings: Settings | None = None,
    *,
    enrichment_transport: httpx.AsyncBaseTransport | None = None,
    llm: LLMClient | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level, settings.log_json, settings.service_name)
    log = get_logger("startup")

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # --- startup: load the artifact once, not per request -------------------
        model, version, error = None, None, None
        try:
            loaded = load_artifact(settings.model_dir, settings.model_version)
            model, version = loaded.model, loaded.version
            log.info("model_loaded", model_version=version, sha256=loaded.metadata["model_sha256"][:12])
        except ArtifactError as exc:
            error = f"{type(exc).__name__}: {exc}"
            # Not fatal: we stay alive (liveness OK), report not-ready, and fall back to rules.
            log.error("model_load_failed", error=error)

        app.state.model_load_error = error
        app.state.scorer = FraudScorer(
            model, version, DecisionPolicy(settings.review_threshold, settings.decline_threshold)
        )

        feature_store = None
        if settings.enrichment_base_url:
            feature_store = HttpFeatureStore(
                settings.enrichment_base_url,
                timeout_s=settings.enrichment_timeout_s,
                policy=RetryPolicy(
                    max_attempts=settings.enrichment_max_attempts,
                    deadline_s=settings.enrichment_deadline_s,
                    rng=random.Random(),
                ),
                budget=RetryBudget(ratio=settings.retry_budget_ratio),
                transport=enrichment_transport,
            )
        app.state.scoring_service = ScoringService(app.state.scorer, feature_store)
        app.state.recent_scores = LRUStore(max_items=1000)
        app.state.llm = llm or build_llm(settings)
        log.info("service_started", environment=settings.environment, version=__version__)
        yield
        # --- shutdown: close network clients cleanly -----------------------------
        if feature_store is not None:
            await feature_store.aclose()
        log.info("service_stopped")

    app = FastAPI(
        title="Kestrel Pay fraud-service",
        version=__version__,
        description="Scores card transactions for fraud. Lab 1 of Build Production-Grade AI Systems.",
        lifespan=lifespan,
    )
    app.add_middleware(RequestIdMiddleware)
    app.include_router(router)
    return app
