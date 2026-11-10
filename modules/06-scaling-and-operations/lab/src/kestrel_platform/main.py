"""App factory for the kestrel-platform service.

Run locally:  uv run uvicorn kestrel_platform.main:app --port 8080
"""

from __future__ import annotations

import random
import time
import uuid

import structlog
from fastapi import FastAPI, Request
from prometheus_client import Counter, Histogram

from kestrel_platform.api.routes import router
from kestrel_platform.config import Settings, get_settings

log = structlog.get_logger()

# Metric names match the PromQL in k8s/rollout/analysis-template.yaml.
REQUESTS = Counter(
    "kestrel_requests_total", "HTTP requests", ["service", "version", "route", "status"]
)
LATENCY = Histogram(
    "kestrel_request_latency_seconds",
    "HTTP request latency",
    ["service", "version", "route"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title=settings.app_name, version=settings.app_version)
    app.state.settings = settings
    app.state.fault_rng = random.Random(settings.fault_seed)
    app.state.warm = True  # a real model server would flip this after loading weights

    @app.middleware("http")
    async def observe(request: Request, call_next):  # type: ignore[no-untyped-def]
        request_id = request.headers.get("x-request-id", uuid.uuid4().hex)
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start
        route = request.url.path
        if route not in ("/metrics", "/health", "/ready"):
            REQUESTS.labels(settings.app_name, settings.app_version, route, str(response.status_code)).inc()
            LATENCY.labels(settings.app_name, settings.app_version, route).observe(elapsed)
        response.headers["x-request-id"] = request_id
        response.headers["x-app-version"] = settings.app_version
        return response

    app.include_router(router)
    log.info("app_created", version=settings.app_version, fault_error_rate=settings.fault_error_rate)
    return app


def __getattr__(name: str):  # lazily build `app` so tests can create their own instances
    if name == "app":
        return create_app()
    raise AttributeError(name)
