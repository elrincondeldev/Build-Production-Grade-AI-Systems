"""App factory. Run with:

    uv run uvicorn kestrel_docs.main:create_app --factory --port 8000
"""

from __future__ import annotations

import time
import uuid

from fastapi import FastAPI, Request

from kestrel_docs import observability as obs
from kestrel_docs.adapters.llm import build_llm
from kestrel_docs.api.routes import router
from kestrel_docs.config import Settings, get_settings
from kestrel_docs.domain.assistant import DocsAssistant
from kestrel_docs.domain.handbook import load_handbook
from kestrel_docs.domain.prompt_registry import PromptRegistry
from kestrel_docs.domain.retrieval import BM25Retriever


def build_assistant(settings: Settings) -> DocsAssistant:
    chunks = load_handbook(settings.data_dir / "handbook", sanitize=settings.sanitize_context)
    return DocsAssistant(
        BM25Retriever(chunks),
        build_llm(settings),
        PromptRegistry(settings.prompt_registry_dir, settings.prompt_name),
        top_k=settings.top_k,
        history_turns=settings.history_turns,
        cache_enabled=settings.cache_enabled,
    )


def create_app(settings: Settings | None = None, assistant: DocsAssistant | None = None) -> FastAPI:
    settings = settings or get_settings()
    obs.configure_tracing(settings.otel_exporter, otlp_endpoint=settings.otlp_endpoint)

    app = FastAPI(title="Kestrel docs-assistant (Module 4)", version="0.4.0")
    app.state.assistant = assistant or build_assistant(settings)
    obs.PROMPT_INFO.labels(settings.prompt_name, app.state.assistant.registry.active_version()).set(1)

    @app.middleware("http")
    async def request_metrics(request: Request, call_next):  # noqa: ANN001, ANN202
        request.state.request_id = request.headers.get("x-request-id", uuid.uuid4().hex)
        start = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["x-request-id"] = request.state.request_id
            return response
        finally:
            # Use the route *template*, never the raw path: raw paths with IDs
            # explode metric cardinality and can take Prometheus down.
            route = request.scope.get("route")
            label = getattr(route, "path", "unmatched")
            if label != "/metrics":
                obs.REQUEST_LATENCY.labels(label).observe(time.perf_counter() - start)
                obs.REQUESTS.labels(label, str(status)).inc()

    app.include_router(router)
    return app
