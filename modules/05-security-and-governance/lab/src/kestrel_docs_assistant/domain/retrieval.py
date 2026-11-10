"""Permission-aware BM25 retrieval.

📖 See lesson 5.3 "Authentication and authorization".

The rule this module enforces: **filter by permission BEFORE ranking**.
A chunk the user may not read is never scored, never returned, never placed in
a prompt, and never influences the statistics (IDF) used to rank other chunks.

Post-filtering (rank everything, drop forbidden results afterwards) looks
equivalent but is not: it leaks through result counts, through scores, and the
moment someone forgets the filter on a new code path.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache

from .documents import Chunk
from .text import tokenize


@dataclass(frozen=True)
class ScoredChunk:
    chunk: Chunk
    score: float


class PermissionAwareBM25:
    def __init__(self, chunks: list[Chunk], *, k1: float = 1.5, b: float = 0.75) -> None:
        self.chunks = chunks
        self.k1, self.b = k1, b
        self._tokens = [Counter(tokenize(c.title + " " + c.text)) for c in chunks]
        self._lengths = [sum(t.values()) for t in self._tokens]

    @lru_cache(maxsize=64)
    def _partition(self, allowed: frozenset[str]) -> tuple[tuple[int, ...], dict[str, float], float]:
        """Indices + IDF + avg length computed ONLY over chunks this role may see."""
        idx = tuple(i for i, c in enumerate(self.chunks) if c.access in allowed)
        n = len(idx) or 1
        df: Counter[str] = Counter()
        for i in idx:
            df.update(self._tokens[i].keys())
        idf = {term: math.log(1 + (n - f + 0.5) / (f + 0.5)) for term, f in df.items()}
        avg_len = sum(self._lengths[i] for i in idx) / n
        return idx, idf, avg_len

    def search(self, query: str, allowed: frozenset[str], k: int = 4) -> list[ScoredChunk]:
        idx, idf, avg_len = self._partition(allowed)
        q_terms = tokenize(query)
        results: list[ScoredChunk] = []
        for i in idx:  # ← pre-filter: forbidden chunks are not even iterated
            tf, length = self._tokens[i], self._lengths[i]
            score = 0.0
            for term in q_terms:
                if term not in tf:
                    continue
                f = tf[term]
                score += idf.get(term, 0.0) * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * length / avg_len))
            if score > 0:
                results.append(ScoredChunk(self.chunks[i], round(score, 4)))
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:k]
