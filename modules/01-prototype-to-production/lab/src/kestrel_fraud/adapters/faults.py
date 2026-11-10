"""Deterministic fault injection for httpx (📖 lesson 1.3, "Break it" experiments).

Wraps any httpx transport and makes the first N calls (or a seeded random
fraction of calls) fail with a status code or a timeout. Tests use it to prove
the retry logic works without a real flaky network.
"""

from __future__ import annotations

import random

import httpx


class FaultInjectingTransport(httpx.AsyncBaseTransport):
    def __init__(
        self,
        inner: httpx.AsyncBaseTransport,
        *,
        fail_first: int = 0,
        fail_rate: float = 0.0,
        status_code: int = 503,
        timeout: bool = False,
        seed: int = 0,
    ) -> None:
        self.inner = inner
        self.fail_first = fail_first
        self.fail_rate = fail_rate
        self.status_code = status_code
        self.timeout = timeout
        self.rng = random.Random(seed)
        self.calls = 0
        self.requests: list[httpx.Request] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.calls += 1
        self.requests.append(request)
        should_fail = self.calls <= self.fail_first or self.rng.random() < self.fail_rate
        if should_fail:
            if self.timeout:
                raise httpx.ReadTimeout("injected timeout", request=request)
            return httpx.Response(self.status_code, json={"error": "injected fault"}, request=request)
        return await self.inner.handle_async_request(request)
