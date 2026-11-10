"""HTTP layer: schemas, routes and per-request metrics. No business logic here."""

from __future__ import annotations

from collections import OrderedDict
from typing import Literal

from fastapi import APIRouter, HTTPException, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel, Field

from kestrel_docs import observability as obs
from kestrel_docs.adapters.llm import Message
from kestrel_docs.domain.assistant import DocsAssistant
from kestrel_docs.domain.handbook import ROLE_ACCESS

router = APIRouter()

# request_id -> prompt_version, so feedback can be attributed to a prompt version.
_recent_requests: OrderedDict[str, str] = OrderedDict()


class Turn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    role: str = "customer"
    history: list[Turn] = Field(default_factory=list)


class AskResponse(BaseModel):
    request_id: str
    answer: str
    citations: list[str]
    refused: bool
    prompt_version: str
    model: str
    cached: bool
    latency_ms: float


class FeedbackRequest(BaseModel):
    request_id: str
    rating: Literal["up", "down"]


def _assistant(request: Request) -> DocsAssistant:
    return request.app.state.assistant


@router.get("/health")
async def health() -> dict:
    """Liveness: the process is up."""
    return {"status": "ok"}


@router.get("/ready")
async def ready(request: Request) -> dict:
    """Readiness: the index is loaded and a prompt is active."""
    assistant = _assistant(request)
    return {
        "status": "ready",
        "chunks": len(assistant.retriever.chunks),
        "prompt_version": assistant.registry.active_version(),
    }


@router.post("/ask", response_model=AskResponse)
async def ask(body: AskRequest, request: Request) -> AskResponse:
    if body.role not in ROLE_ACCESS:
        raise HTTPException(status_code=400, detail=f"unknown role {body.role!r}")
    assistant = _assistant(request)
    history = [Message(t.role, t.content) for t in body.history]
    answer = await assistant.ask(body.question, body.role, history)

    # --- metrics --------------------------------------------------------
    obs.CACHE_LOOKUPS.labels("hit" if answer.cached else "miss").inc()
    obs.ANSWERS.labels(answer.prompt_version).inc()
    if not answer.cached:
        obs.LLM_TOKENS.labels("prompt", answer.model).inc(answer.prompt_tokens)
        obs.LLM_TOKENS.labels("completion", answer.model).inc(answer.completion_tokens)
        obs.RETRIEVAL_TOP_SCORE.observe(answer.retrieved[0].score if answer.retrieved else 0.0)
    if answer.refused:
        obs.REFUSALS.labels(answer.refusal_reason or "model").inc()

    request_id = request.state.request_id
    _recent_requests[request_id] = answer.prompt_version
    if len(_recent_requests) > 10_000:
        _recent_requests.popitem(last=False)

    return AskResponse(
        request_id=request_id,
        answer=answer.text,
        citations=answer.citations,
        refused=answer.refused,
        prompt_version=answer.prompt_version,
        model=answer.model,
        cached=answer.cached,
        latency_ms=round(answer.latency_ms, 2),
    )


@router.post("/feedback", status_code=204)
async def feedback(body: FeedbackRequest) -> Response:
    """Thumbs up/down: the cheapest *online* evaluation signal you can collect."""
    version = _recent_requests.get(body.request_id, "unknown")
    obs.FEEDBACK.labels(body.rating, version).inc()
    return Response(status_code=204)


@router.get("/metrics")
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
