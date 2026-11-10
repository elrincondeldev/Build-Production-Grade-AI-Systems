"""Response caches for LLM answers. 📖 Lesson 3.5.

ExactCache    hit only if the *normalised* request is identical. Zero risk of a wrong
              answer, low hit rate.
SemanticCache hit if a previous question is *similar enough* (cosine >= threshold).
              Higher hit rate, but a false hit serves the answer to a different question.

Both caches key on everything that changes the answer: the question, the prompt
version and the model. In a multi-tenant system you must add the user's permission
scope as well (📖 lesson 5.3), or one user can read another user's cached answer.
"""

from __future__ import annotations

import hashlib
import re
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from kestrel_serving.adapters.embeddings import Embedder


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s€%]", "", text.lower())).strip()


@dataclass
class CacheStats:
    hits: int = 0
    misses: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total else 0.0

    def as_dict(self) -> dict[str, float]:
        return {"hits": self.hits, "misses": self.misses, "hit_rate": round(self.hit_rate, 3)}


class ExactCache:
    def __init__(self, ttl_s: float = 3600, max_entries: int = 10_000, clock: Callable[[], float] = time.monotonic):
        self.ttl_s = ttl_s
        self.max_entries = max_entries
        self._clock = clock
        self._data: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self.stats = CacheStats()

    @staticmethod
    def key(question: str, scope: str = "") -> str:
        return hashlib.sha256(f"{scope}|{normalize(question)}".encode()).hexdigest()

    def get(self, question: str, scope: str = "") -> Any | None:
        k = self.key(question, scope)
        entry = self._data.get(k)
        if entry and self._clock() - entry[0] <= self.ttl_s:
            self._data.move_to_end(k)  # LRU: recently used entries survive eviction
            self.stats.hits += 1
            return entry[1]
        if entry:
            del self._data[k]  # expired
        self.stats.misses += 1
        return None

    def put(self, question: str, value: Any, scope: str = "") -> None:
        k = self.key(question, scope)
        self._data[k] = (self._clock(), value)
        self._data.move_to_end(k)
        while len(self._data) > self.max_entries:
            self._data.popitem(last=False)

    def __len__(self) -> int:
        return len(self._data)


@dataclass
class _SemanticEntry:
    question: str
    scope: str
    created: float
    value: Any


@dataclass
class SemanticHit:
    value: Any
    similarity: float
    matched_question: str


@dataclass
class SemanticCache:
    embedder: Embedder
    threshold: float = 0.92
    ttl_s: float = 3600
    max_entries: int = 10_000
    clock: Callable[[], float] = time.monotonic
    stats: CacheStats = field(default_factory=CacheStats)

    def __post_init__(self) -> None:
        self._entries: list[_SemanticEntry] = []
        self._vectors = np.zeros((0, self.embedder.dim), dtype=np.float32)

    def _evict_expired(self) -> None:
        now = self.clock()
        keep = [i for i, e in enumerate(self._entries) if now - e.created <= self.ttl_s]
        if len(keep) != len(self._entries):
            self._entries = [self._entries[i] for i in keep]
            self._vectors = self._vectors[keep]

    def get(self, question: str, scope: str = "") -> SemanticHit | None:
        self._evict_expired()
        if not self._entries:
            self.stats.misses += 1
            return None
        query = self.embedder.embed([normalize(question)])[0]
        # Linear scan is fine for thousands of entries; use an ANN index beyond that.
        sims = self._vectors @ query  # vectors are L2-normalised, so dot product == cosine
        for i in np.argsort(-sims):
            entry = self._entries[i]
            if sims[i] < self.threshold:
                break
            if entry.scope == scope:
                self.stats.hits += 1
                return SemanticHit(entry.value, float(sims[i]), entry.question)
        self.stats.misses += 1
        return None

    def put(self, question: str, value: Any, scope: str = "") -> None:
        vector = self.embedder.embed([normalize(question)])
        self._entries.append(_SemanticEntry(question, scope, self.clock(), value))
        self._vectors = np.vstack([self._vectors, vector])
        if len(self._entries) > self.max_entries:  # FIFO eviction keeps the demo simple
            self._entries = self._entries[1:]
            self._vectors = self._vectors[1:]

    def __len__(self) -> int:
        return len(self._entries)
