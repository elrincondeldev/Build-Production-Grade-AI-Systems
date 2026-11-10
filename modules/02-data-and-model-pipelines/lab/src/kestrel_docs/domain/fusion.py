"""Reciprocal Rank Fusion (Cormack, Clarke & Büttcher, 2009). 📖 Lesson 2.5.

BM25 scores (0–30) and cosine similarities (0–1) live on different scales, so
you cannot just add them. RRF ignores scores and uses only *ranks*:

    rrf(d) = Σ over retrievers  1 / (k + rank(d))       rank starts at 1, k = 60

A document ranked well by both retrievers beats one ranked first by only one.
"""

from __future__ import annotations


def reciprocal_rank_fusion(rankings: list[list[str]], k: int = 60) -> list[tuple[str, float]]:
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, start=1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank)
    # Sort by score, then by id so ties are deterministic.
    return sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
