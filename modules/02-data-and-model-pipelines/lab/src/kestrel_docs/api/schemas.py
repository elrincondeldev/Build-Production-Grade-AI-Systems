"""HTTP request/response shapes. The API layer only translates HTTP <-> domain (📖 lesson 1.4)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from kestrel_docs.domain.roles import Role


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    role: Role = "customer"  # ⚠️ self-declared for now; lesson 5.3 takes it from a verified token
    mode: Literal["bm25", "dense", "hybrid"] = "hybrid"
    rerank: bool = True
    top_k: int | None = Field(default=None, ge=1, le=10)


class Citation(BaseModel):
    doc_id: str
    title: str


class ChunkOut(BaseModel):
    chunk_id: str
    doc_id: str
    section: str
    access: str
    score: float
    text: str


class AskResponse(BaseModel):
    answer: str
    citations: list[Citation]
    chunks: list[ChunkOut]
    model: str
    latency_ms: float
    notes: list[str]
