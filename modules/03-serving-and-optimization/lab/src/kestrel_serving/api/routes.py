"""HTTP layer only: validation, status codes, serialisation. No business logic here."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

router = APIRouter()


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)


class AskResponse(BaseModel):
    answer: str
    citations: list[str]
    model: str
    cache: str | None
    timings_ms: dict[str, float]
    prompt_tokens: int
    completion_tokens: int


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def ready(request: Request) -> dict[str, object]:
    return {"status": "ready", "chunks_indexed": len(request.app.state.service.retriever.chunks)}


@router.post("/v1/answer", response_model=AskResponse)
async def answer(body: AskRequest, request: Request) -> AskResponse:
    result = await request.app.state.service.answer(body.question)
    return AskResponse(**result.__dict__)


@router.post("/v1/answer/stream")
async def answer_stream(body: AskRequest, request: Request) -> StreamingResponse:
    service = request.app.state.service
    return StreamingResponse(service.stream(body.question), media_type="text/plain; charset=utf-8")


@router.get("/v1/cache/stats")
async def cache_stats(request: Request) -> dict[str, object]:
    s = request.app.state.service
    return {
        "exact": None if s.exact_cache is None else {**s.exact_cache.stats.as_dict(), "size": len(s.exact_cache)},
        "semantic": None
        if s.semantic_cache is None
        else {**s.semantic_cache.stats.as_dict(), "size": len(s.semantic_cache), "threshold": s.semantic_cache.threshold},
    }
