"""Your first API: two endpoints and automatic docs.

📖 See lesson 0.3 "HTTP and APIs".

    uv run uvicorn kestrel_foundations.hello_api:app --reload --port 8000
    open http://localhost:8000/docs
"""

from __future__ import annotations

import uuid

from fastapi import FastAPI, Header
from pydantic import BaseModel, Field


class EchoRequest(BaseModel):
    """The *contract*: FastAPI rejects bad input with 422 before your code runs."""

    message: str = Field(min_length=1, max_length=1000, examples=["hello Kestrel"])
    repeat: int = Field(default=1, ge=1, le=5)


class EchoResponse(BaseModel):
    echo: str
    length: int
    request_id: str


def create_app() -> FastAPI:
    """App factory: tests and servers each build a fresh app (pattern reused in Module 1)."""
    app = FastAPI(title="Kestrel hello API", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        """Cheap liveness check: 'the process is up'. Load balancers call this constantly."""
        return {"status": "ok"}

    @app.post("/echo", response_model=EchoResponse)
    def echo(body: EchoRequest, x_request_id: str | None = Header(default=None)) -> EchoResponse:
        # Reuse the caller's request ID if given, so one request can be traced across services.
        request_id = x_request_id or str(uuid.uuid4())
        text = " ".join([body.message] * body.repeat)
        return EchoResponse(echo=text, length=len(text), request_id=request_id)

    return app


app = create_app()
