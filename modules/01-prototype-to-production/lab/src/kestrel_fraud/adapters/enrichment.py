"""HTTP client for the online feature store (📖 lessons 1.2 and 1.3).

In production, per-customer aggregates such as "transactions in the last 24h"
live in an online feature store (Feast, Redis, a feature service…) because the
caller of /v1/score does not know them. This client calls that store with:

* a per-attempt **timeout** (httpx.Timeout)
* **retries** with backoff + jitter, bounded by a **deadline** and a **retry budget**
* the caller's **X-Request-ID** forwarded, so one request can be traced across services

It converts every failure into ``EnrichmentUnavailable`` so the domain can degrade gracefully.
"""

from __future__ import annotations

import httpx

from ..domain.service import EnrichmentUnavailable
from ..logging import get_logger
from .request_context import current_request_id
from .retry import RetryableError, RetryBudget, RetryPolicy, RetryStats, call_with_retries

log = get_logger(__name__)

RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class HttpFeatureStore:
    def __init__(
        self,
        base_url: str,
        *,
        timeout_s: float = 0.3,
        policy: RetryPolicy | None = None,
        budget: RetryBudget | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.client = httpx.AsyncClient(
            base_url=base_url,
            timeout=httpx.Timeout(timeout_s, connect=min(timeout_s, 0.2)),
            transport=transport,
        )
        self.policy = policy or RetryPolicy()
        self.budget = budget if budget is not None else RetryBudget()
        self.last_stats = RetryStats()

    async def _get_once(self, customer_id: str) -> dict[str, float]:
        headers = {}
        if (rid := current_request_id()) is not None:
            headers["X-Request-ID"] = rid
        try:
            resp = await self.client.get(f"/v1/customers/{customer_id}/features", headers=headers)
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise RetryableError(f"{type(exc).__name__}: {exc}") from exc
        if resp.status_code in RETRYABLE_STATUS:
            raise RetryableError(f"HTTP {resp.status_code}")
        if resp.status_code >= 400:
            # 4xx: our request is wrong; retrying would only add load.
            raise EnrichmentUnavailable(f"non-retryable HTTP {resp.status_code}")
        return resp.json()

    async def get_customer_features(self, customer_id: str) -> dict[str, float]:
        stats = RetryStats()
        self.last_stats = stats

        def on_retry(attempt: int, delay: float, exc: Exception) -> None:
            log.warning("enrichment_retry", attempt=attempt, sleep_s=round(delay, 3), error=str(exc))

        try:
            return await call_with_retries(
                lambda: self._get_once(customer_id), self.policy, self.budget, on_retry=on_retry, stats=stats
            )
        except RetryableError as exc:
            log.error("enrichment_failed", attempts=stats.attempts, reason=stats.gave_up_reason, error=str(exc))
            raise EnrichmentUnavailable(str(exc)) from exc

    async def aclose(self) -> None:
        await self.client.aclose()
