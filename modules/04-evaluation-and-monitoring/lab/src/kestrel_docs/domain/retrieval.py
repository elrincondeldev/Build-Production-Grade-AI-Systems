"""Keyword (BM25) retrieval with role-based filtering.

Module 2 (lesson 2.5) adds dense vectors and reranking. Here we keep the
retriever simple on purpose: Module 4 is about *measuring* the system, and a
measurable baseline beats a clever one you can't evaluate.
"""

from __future__ import annotations

from dataclasses import dataclass

from rank_bm25 import BM25Okapi

from kestrel_docs.domain.handbook import ROLE_ACCESS, Chunk
from kestrel_docs.domain.text import content_tokens


@dataclass(frozen=True)
class Retrieved:
    chunk: Chunk
    score: float


class BM25Retriever:
    def __init__(self, chunks: list[Chunk]) -> None:
        self.chunks = chunks
        corpus = [content_tokens(f"{c.title} {c.text}") for c in chunks]
        self._bm25 = BM25Okapi(corpus)

    def retrieve(self, query: str, role: str, k: int = 3) -> list[Retrieved]:
        allowed = ROLE_ACCESS.get(role, frozenset({"public"}))
        query_tokens = content_tokens(query)
        if not query_tokens:
            return []
        scores = self._bm25.get_scores(query_tokens)
        ranked = sorted(
            (
                Retrieved(chunk, float(score))
                for chunk, score in zip(self.chunks, scores, strict=True)
                # Filter inside the retriever, before top-k: a chunk the user may
                # not see must never reach the prompt, not even as "context".
                # (Filtering after top-k would also silently lose good results.)
                # 📖 See lesson 5.3.
                if chunk.access in allowed and score > 0
            ),
            key=lambda r: r.score,
            reverse=True,
        )
        return ranked[:k]
