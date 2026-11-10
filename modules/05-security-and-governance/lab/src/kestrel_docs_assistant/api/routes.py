"""HTTP layer: authentication, rate limiting, request IDs. No business logic here."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from ..adapters.tokens import Principal, TokenError, decode_token
from ..domain.contracts import AssistantAnswer

router = APIRouter()
_bearer = HTTPBearer(auto_error=False)


class AskRequest(BaseModel):
    # Hard ceiling at the HTTP edge; the policy bundle sets the (lower) business limit.
    question: str = Field(min_length=1, max_length=20_000)


def get_principal(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> Principal:
    """FastAPI dependency: every protected route gets a verified Principal or a 401."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "missing bearer token", headers={"WWW-Authenticate": "Bearer"}
        )
    settings = request.app.state.settings
    try:
        return decode_token(
            credentials.credentials, settings.jwt_secret, issuer=settings.jwt_issuer, audience=settings.jwt_audience
        )
    except TokenError as exc:
        request.app.state.log.warning("auth_failed", reason=str(exc))
        # Same generic message for every failure: don't tell attackers *why* it failed.
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "invalid or expired token", headers={"WWW-Authenticate": "Bearer"}
        ) from exc


def request_id(x_request_id: Annotated[str | None, Header()] = None) -> str:
    return x_request_id if x_request_id and len(x_request_id) <= 64 else str(uuid.uuid4())


@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
def readyz(request: Request) -> dict[str, object]:
    state = request.app.state
    return {"status": "ready", "chunks": len(state.index.chunks), "policy_version": state.assistant.bundle.version}


@router.get("/v1/whoami")
def whoami(principal: Annotated[Principal, Depends(get_principal)]) -> dict[str, str]:
    return {"sub": principal.sub, "role": principal.role}


@router.post("/v1/ask", response_model=AssistantAnswer)
async def ask(
    body: AskRequest,
    request: Request,
    principal: Annotated[Principal, Depends(get_principal)],
    rid: Annotated[str, Depends(request_id)],
) -> AssistantAnswer:
    if not request.app.state.rate_limiter.allow(principal.sub):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "rate limit exceeded", headers={"Retry-After": "60"})
    result = await request.app.state.assistant.answer(body.question, principal, rid)
    request.app.state.log.info(
        "ask_completed", request_id=rid, sub=principal.sub, role=principal.role, refused=result.refused, reason=result.reason
    )
    return result
