"""App factory. Run with:

    uv run uvicorn kestrel_docs_assistant.main:create_app --factory --port 8000
"""

from __future__ import annotations

import logging

import structlog
from fastapi import FastAPI

from .adapters.llm import LLMClient, build_llm
from .api.routes import router
from .config import Settings, get_settings
from .domain.assistant import DocsAssistant, Layers
from .domain.audit import AuditLog
from .domain.documents import chunk_document, load_corpus
from .domain.guardrails import HeuristicInjectionDetector
from .domain.pii import redact_structure
from .domain.ratelimit import RateLimiter
from .domain.registry import PolicyRegistry
from .domain.retrieval import PermissionAwareBM25


def _redact_processor(_logger: object, _name: str, event_dict: dict) -> dict:
    """structlog processor: no PII ever reaches the log pipeline (📖 lesson 5.4)."""
    return redact_structure(event_dict)  # type: ignore[return-value]


def configure_logging() -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            _redact_processor,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    )


def create_app(settings: Settings | None = None, llm: LLMClient | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging()
    log = structlog.get_logger("docs-assistant")

    documents = load_corpus(settings.handbook_dir, sanitize_content=settings.sanitize_ingest)
    for doc in documents:
        if doc.findings or not doc.trusted:
            log.warning("ingest_flagged", doc_id=doc.doc_id, findings=list(doc.findings), trusted=doc.trusted)
    chunks = [c for doc in documents for c in chunk_document(doc)]
    index = PermissionAwareBM25(chunks)

    bundle = PolicyRegistry(settings.registry_dir).active_bundle()
    assistant = DocsAssistant(
        index=index,
        llm=llm or build_llm(settings),
        bundle=bundle,
        detector=HeuristicInjectionDetector(),
        audit=AuditLog(settings.audit_log_path),
        layers=Layers(
            input_guardrails=settings.input_guardrails,
            scan_retrieved_chunks=settings.scan_retrieved_chunks,
            output_guardrails=settings.output_guardrails,
        ),
    )

    app = FastAPI(title="Kestrel docs-assistant (secured)", version="0.5.0")
    app.state.settings = settings
    app.state.log = log
    app.state.index = index
    app.state.assistant = assistant
    app.state.rate_limiter = RateLimiter(settings.rate_limit_per_minute)
    app.include_router(router)
    log.info("startup", chunks=len(chunks), policy_version=bundle.version, llm=settings.llm_provider)
    return app
