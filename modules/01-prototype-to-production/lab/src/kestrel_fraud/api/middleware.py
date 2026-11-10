"""Request IDs and access logs (📖 lesson 1.4).

A request ID is a unique string attached to one request. It is:
* taken from the incoming ``X-Request-ID`` header (so an upstream gateway's ID is kept),
  or generated if absent,
* bound to every log line written while handling the request,
* forwarded to downstream services (see adapters/enrichment.py),
* returned in the response header, so a user can quote it in a support ticket.
"""

from __future__ import annotations

import re
import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from ..adapters.request_context import reset_request_id, set_request_id
from ..logging import get_logger

REQUEST_ID_HEADER = "X-Request-ID"
_VALID_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")  # never trust header contents blindly
log = get_logger("access")


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        incoming = request.headers.get(REQUEST_ID_HEADER, "")
        request_id = incoming if _VALID_ID.match(incoming) else uuid.uuid4().hex
        token = set_request_id(request_id)
        request.state.request_id = request_id
        structlog.contextvars.bind_contextvars(request_id=request_id)
        start = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers[REQUEST_ID_HEADER] = request_id
            return response
        finally:
            # Note: for streaming responses (SSE) this fires when the headers are sent,
            # not when the stream ends. Module 4 uses tracing spans to time full streams.
            log.info(
                "http_request",
                method=request.method,
                path=request.url.path,
                status=status,
                duration_ms=round((time.perf_counter() - start) * 1000, 2),
            )
            structlog.contextvars.unbind_contextvars("request_id")
            reset_request_id(token)
