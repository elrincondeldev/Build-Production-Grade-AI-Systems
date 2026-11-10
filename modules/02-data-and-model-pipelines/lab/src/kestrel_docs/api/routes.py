from __future__ import annotations

from fastapi import APIRouter, Request

from kestrel_docs.api.schemas import AskRequest, AskResponse, ChunkOut, Citation
from kestrel_docs.domain.answer import answer_question
from kestrel_docs.service import Services

router = APIRouter()


@router.get("/healthz")
def healthz() -> dict:
    """Liveness: the process is up."""
    return {"status": "ok"}


@router.get("/readyz")
def readyz(request: Request) -> dict:
    """Readiness: the index is built and can serve queries."""
    svc: Services | None = getattr(request.app.state, "services", None)
    if svc is None:
        from fastapi import HTTPException

        raise HTTPException(503, "index not built yet")
    return {"status": "ready", "documents": len(svc.index.docs), "chunks": len(svc.index.chunks)}


@router.post("/v1/ask", response_model=AskResponse)
async def ask(body: AskRequest, request: Request) -> AskResponse:
    svc: Services = request.app.state.services
    result = await answer_question(
        body.question, body.role, svc.retriever, svc.llm,
        mode=body.mode, top_k=body.top_k or svc.settings.top_k, rerank=body.rerank,
        token_budget=svc.settings.context_token_budget,
    )
    used = result.context.used if result.context else []
    return AskResponse(
        answer=result.answer,
        citations=[Citation(doc_id=d, title=svc.index.docs[d].title) for d in result.citations],
        chunks=[
            ChunkOut(chunk_id=r.chunk.chunk_id, doc_id=r.chunk.doc_id, section=r.chunk.section,
                     access=r.chunk.access, score=round(r.score, 4), text=r.chunk.text)
            for r in used
        ],
        model=result.model,
        latency_ms=round(result.latency_ms, 1),
        notes=result.notes,
    )
