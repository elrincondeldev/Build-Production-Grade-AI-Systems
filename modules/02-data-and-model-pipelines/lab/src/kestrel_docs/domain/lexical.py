"""Keyword search with BM25. 📖 Lesson 2.5.

BM25 scores a chunk higher when it contains the query's words, especially rare
words (IDF), with diminishing returns for repetition (k1) and a penalty for
long chunks (b). It shines on exact terms: "SEV1", "T+2", "€250", "CVV".
"""

from __future__ import annotations

import re

from rank_bm25 import BM25Okapi

from kestrel_docs.domain.chunking import Chunk

STOPWORDS = frozenset(
    "a an the and or of to in on for with is are be can i my me do does how what when which who "
    "if it at by from as this that there i'm you your we our".split()
)
_TOKEN = re.compile(r"[a-z0-9€%+]+")


def tokenize(text: str) -> list[str]:
    tokens = []
    for t in _TOKEN.findall(text.lower()):
        if t in STOPWORDS:
            continue
        # Tiny stemmer: 'refunds' -> 'refund', 'days' -> 'day'. Real systems use Snowball/Porter.
        if len(t) > 3 and t.endswith("s") and not t.endswith("ss"):
            t = t[:-1]
        tokens.append(t)
    return tokens


class BM25Index:
    def __init__(self, chunks: list[Chunk], k1: float = 1.5, b: float = 0.75):
        self.chunks = chunks
        self._bm25 = BM25Okapi([tokenize(c.embed_text) for c in chunks], k1=k1, b=b)

    def search(self, query: str, k: int, allowed_access: list[str] | None = None) -> list[tuple[str, float]]:
        scores = self._bm25.get_scores(tokenize(query))
        ranked = sorted(range(len(self.chunks)), key=lambda i: scores[i], reverse=True)
        out = []
        for i in ranked:
            c = self.chunks[i]
            if scores[i] <= 0 or (allowed_access is not None and c.access not in allowed_access):
                continue
            out.append((c.chunk_id, float(scores[i])))
            if len(out) == k:
                break
        return out
