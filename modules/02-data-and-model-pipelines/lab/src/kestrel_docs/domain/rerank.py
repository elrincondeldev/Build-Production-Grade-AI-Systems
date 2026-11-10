"""Rerankers: a second, more careful pass over a short candidate list. 📖 Lesson 2.5.

Retrievers must be fast over *millions* of chunks, so they compare query and
chunk independently. A reranker looks at (query, chunk) *together* but only for
~20 candidates. A cross-encoder model does this best; the lexical reranker here
is a transparent, dependency-free stand-in so you can see the interface.
"""

from __future__ import annotations

from typing import Protocol

from kestrel_docs.domain.chunking import Chunk
from kestrel_docs.domain.lexical import tokenize


class Reranker(Protocol):
    def rerank(self, query: str, chunks: list[Chunk]) -> list[tuple[Chunk, float]]: ...


class LexicalOverlapReranker:
    """Score = share of query terms in the chunk, plus a bonus for terms in its title/section."""

    def rerank(self, query: str, chunks: list[Chunk]) -> list[tuple[Chunk, float]]:
        q = set(tokenize(query))
        if not q:
            return [(c, 0.0) for c in chunks]
        scored = []
        for order, c in enumerate(chunks):
            body = set(tokenize(c.text))
            head = set(tokenize(c.header))
            score = len(q & body) / len(q) + 0.5 * len(q & head) / len(q) - 0.001 * order  # keep fused order on ties
            scored.append((c, score))
        return sorted(scored, key=lambda cs: cs[1], reverse=True)


class CrossEncoderReranker:
    """Real reranker. Install with: uv sync --extra semantic"""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        from sentence_transformers import CrossEncoder  # optional dependency

        self._model = CrossEncoder(model_name)

    def rerank(self, query: str, chunks: list[Chunk]) -> list[tuple[Chunk, float]]:
        scores = self._model.predict([(query, c.embed_text) for c in chunks])
        return sorted(zip(chunks, map(float, scores)), key=lambda cs: cs[1], reverse=True)


class NoReranker:
    def rerank(self, query: str, chunks: list[Chunk]) -> list[tuple[Chunk, float]]:
        return [(c, 1.0 / (i + 1)) for i, c in enumerate(chunks)]
