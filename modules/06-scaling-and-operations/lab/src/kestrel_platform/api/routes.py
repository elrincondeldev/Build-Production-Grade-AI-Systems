"""HTTP layer: health, readiness, scoring and Prometheus metrics.

📖 Lesson 6.1 (probes) and lesson 6.4 (the metrics the canary analysis reads).
"""

from __future__ import annotations

import asyncio
import random

from fastapi import APIRouter, HTTPException, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from kestrel_platform.domain.scoring import Score, Transaction, score

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness: "is the process alive?" Keep it dumb. Never check dependencies here,
    or a database blip will make Kubernetes restart every pod at once."""
    return {"status": "ok"}


@router.get("/ready")
async def ready(request: Request) -> Response:
    """Readiness: "should I receive traffic right now?" Fails while warming up or draining."""
    state = request.app.state
    if not state.settings.ready or not state.warm:
        return Response(content='{"status":"not ready"}', status_code=503, media_type="application/json")
    return Response(content='{"status":"ready"}', media_type="application/json")


@router.post("/v1/score", response_model=Score)
async def score_transaction(txn: Transaction, request: Request) -> Score:
    settings = request.app.state.settings
    rng: random.Random = request.app.state.fault_rng
    if settings.fault_extra_latency_ms:
        await asyncio.sleep(settings.fault_extra_latency_ms / 1000)
    if settings.fault_error_rate and rng.random() < settings.fault_error_rate:
        raise HTTPException(status_code=500, detail="injected fault")
    return score(txn, model_version=settings.app_version)


@router.get("/metrics")
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

