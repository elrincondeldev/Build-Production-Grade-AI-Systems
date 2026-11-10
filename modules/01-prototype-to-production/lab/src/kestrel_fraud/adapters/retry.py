"""Retries done right: timeouts, exponential backoff, full jitter, deadlines and a budget (📖 lesson 1.3).

Naive retries turn a small outage into a big one: if every client retries 3
times, a struggling dependency suddenly receives 4x the traffic (a "retry
storm"). Four safeguards prevent that:

1. **Only retry what can succeed next time**: timeouts, connection errors, 429 and 5xx.
   Never retry a 400: the request is wrong and will stay wrong.
2. **Exponential backoff with full jitter**: wait ``uniform(0, min(cap, base * 2**attempt))``.
   The randomness spreads retries out so clients do not hammer in sync.
3. **A deadline**: never start a retry that cannot finish before the caller gives up.
4. **A retry budget**: retries may add at most ``ratio`` (e.g. 10%) extra load.
   When the dependency is really down, the budget runs dry and we fail fast.
"""

from __future__ import annotations

import asyncio
import random
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TypeVar

T = TypeVar("T")


class RetryableError(Exception):
    """Wraps an error that is worth retrying."""


@dataclass
class RetryBudget:
    """Token bucket: every first attempt deposits ``ratio`` tokens; every retry spends 1.

    With ratio=0.1, after 100 requests you can afford 10 retries. ``min_tokens``
    lets a quiet service still retry a little. Not thread-safe; one per event loop.
    """

    ratio: float = 0.1
    max_tokens: float = 10.0
    tokens: float = 3.0

    def record_request(self) -> None:
        self.tokens = min(self.max_tokens, self.tokens + self.ratio)

    def try_spend(self) -> bool:
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False


@dataclass
class RetryPolicy:
    max_attempts: int = 3
    base_delay_s: float = 0.05
    max_delay_s: float = 1.0
    deadline_s: float = 1.0
    rng: random.Random = field(default_factory=random.Random)

    def backoff(self, retry_number: int) -> float:
        """Full jitter. retry_number starts at 1 for the first retry."""
        cap = min(self.max_delay_s, self.base_delay_s * (2 ** (retry_number - 1)))
        return self.rng.uniform(0, cap)


@dataclass
class RetryStats:
    attempts: int = 0
    sleeps: list[float] = field(default_factory=list)
    gave_up_reason: str | None = None


async def call_with_retries(
    fn: Callable[[], Awaitable[T]],
    policy: RetryPolicy,
    budget: RetryBudget | None = None,
    *,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    clock: Callable[[], float] = time.monotonic,
    on_retry: Callable[[int, float, Exception], None] | None = None,
    stats: RetryStats | None = None,
) -> T:
    """Call ``fn`` until it succeeds, a non-retryable error occurs, or a safeguard says stop."""
    stats = stats if stats is not None else RetryStats()
    start = clock()
    if budget is not None:
        budget.record_request()

    attempt = 0
    while True:
        attempt += 1
        stats.attempts = attempt
        try:
            return await fn()
        except RetryableError as exc:
            if attempt >= policy.max_attempts:
                stats.gave_up_reason = "max_attempts"
                raise
            delay = policy.backoff(attempt)
            if clock() - start + delay >= policy.deadline_s:
                stats.gave_up_reason = "deadline"
                raise
            if budget is not None and not budget.try_spend():
                stats.gave_up_reason = "budget_exhausted"
                raise
            if on_retry is not None:
                on_retry(attempt, delay, exc)
            stats.sleeps.append(delay)
            await sleep(delay)
