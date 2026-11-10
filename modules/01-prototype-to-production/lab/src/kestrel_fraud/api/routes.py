"""HTTP routes (📖 lessons 1.3 and 1.4)."""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse, StreamingResponse

from ..adapters.llm import Message
from ..domain.features import InvalidTransaction
from ..domain.scoring import ScoreResult
from .schemas import HealthResponse, ReadyResponse, ScoreRequest, ScoreResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["ops"])
async def health() -> HealthResponse:
    """Liveness: "is the process alive and able to answer HTTP?" Never checks dependencies.

    If liveness depended on the model or a database, a dependency outage would make
    Kubernetes restart every healthy pod in a loop, turning a partial outage into a total one.
    """
    return HealthResponse(status="ok")


@router.get("/ready", response_model=ReadyResponse, tags=["ops"])
async def ready(request: Request) -> JSONResponse:
    """Readiness: "should the load balancer send me traffic?" True only once the
    model artifact is loaded *and* its checksum verified."""
    state = request.app.state
    if state.scorer.has_model:
        body = ReadyResponse(status="ready", model_version=state.scorer.model_version)
        return JSONResponse(body.model_dump(), status_code=status.HTTP_200_OK)
    body = ReadyResponse(status="not_ready", model_version=None, reason=state.model_load_error)
    return JSONResponse(body.model_dump(), status_code=status.HTTP_503_SERVICE_UNAVAILABLE)


@router.post("/v1/score", response_model=ScoreResponse, tags=["scoring"])
async def score(payload: ScoreRequest, request: Request) -> ScoreResponse:
    try:
        result = await request.app.state.scoring_service.score(payload.to_domain())
    except InvalidTransaction as exc:  # business validation beyond the schema
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    request.app.state.recent_scores.put(result.transaction_id, result)
    return ScoreResponse.from_result(result, request.state.request_id)


EXPLAIN_SYSTEM_PROMPT = (
    "You are a fraud analyst assistant at Kestrel Pay. Explain to a risk analyst, in at most "
    "4 sentences, why this transaction received its score. Only use the facts provided."
)


def _explain_prompt(r: ScoreResult) -> str:
    reasons = "; ".join(r.reasons) or "no individual risk signal fired"
    return (
        f"Transaction {r.transaction_id} scored {r.score:.2f} (decision: {r.decision}, "
        f"source: {r.source}). Risk signals: {reasons}."
    )


@router.get("/v1/explain/{transaction_id}", tags=["scoring"])
async def explain(transaction_id: str, request: Request) -> StreamingResponse:
    """Stream an LLM explanation of a previously scored transaction as Server-Sent Events.

    Streaming means the analyst sees the first words after ~one token's latency
    instead of waiting for the whole answer (lesson 1.3).
    """
    result: ScoreResult | None = request.app.state.recent_scores.get(transaction_id)
    if result is None:
        raise HTTPException(status_code=404, detail="unknown transaction_id: score it first via POST /v1/score")

    llm = request.app.state.llm
    messages = [Message("system", EXPLAIN_SYSTEM_PROMPT), Message("user", _explain_prompt(result))]

    async def event_stream() -> AsyncIterator[str]:
        async for token in llm.stream(messages, max_tokens=120):
            # SSE frame: "data: <payload>\n\n". Newlines inside data must be split.
            for line in token.splitlines() or [""]:
                yield f"data: {line}\n"
            yield "\n"
            if await request.is_disconnected():  # stop generating if the client left
                return
        yield "event: done\ndata: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})
