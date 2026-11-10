"""In-memory sliding-window rate limiter (per user).

📖 See lesson 5.1, OWASP LLM10 "Unbounded Consumption". Every LLM call costs money;
without a per-identity limit, one leaked token or one runaway script can burn
the month's budget overnight. In production use a shared store (e.g. Redis) so
the limit holds across replicas, and limit tokens, not just requests.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self, limit: int, window_s: float = 60.0) -> None:
        self.limit, self.window_s = limit, window_s
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        hits = self._hits[key]
        while hits and now - hits[0] >= self.window_s:
            hits.popleft()
        if len(hits) >= self.limit:
            return False
        hits.append(now)
        return True
