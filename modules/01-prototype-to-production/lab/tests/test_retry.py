import httpx
import pytest

from kestrel_fraud.adapters.enrichment import HttpFeatureStore
from kestrel_fraud.adapters.retry import (
    RetryableError,
    RetryBudget,
    RetryPolicy,
    RetryStats,
    call_with_retries,
)
from kestrel_fraud.domain.service import EnrichmentUnavailable

from .conftest import feature_store_transport

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


class FakeClock:
    """Time only moves when we 'sleep', so tests are instant and deterministic."""

    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def flaky(failures: int):
    calls = {"n": 0}

    async def fn():
        calls["n"] += 1
        if calls["n"] <= failures:
            raise RetryableError("boom")
        return "ok"

    return fn, calls


async def test_succeeds_after_transient_failures():
    clock = FakeClock()
    fn, calls = flaky(2)
    result = await call_with_retries(fn, RetryPolicy(max_attempts=3), sleep=clock.sleep, clock=clock)
    assert result == "ok" and calls["n"] == 3


async def test_backoff_is_exponential_with_full_jitter():
    policy = RetryPolicy(base_delay_s=0.1, max_delay_s=10)
    for retry_number, cap in [(1, 0.1), (2, 0.2), (3, 0.4), (4, 0.8)]:
        samples = [policy.backoff(retry_number) for _ in range(200)]
        assert all(0 <= s <= cap for s in samples)
        assert max(samples) > cap * 0.5  # jitter actually spreads values across the range


async def test_gives_up_after_max_attempts():
    clock = FakeClock()
    fn, calls = flaky(10)
    stats = RetryStats()
    with pytest.raises(RetryableError):
        await call_with_retries(fn, RetryPolicy(max_attempts=3), sleep=clock.sleep, clock=clock, stats=stats)
    assert calls["n"] == 3 and stats.gave_up_reason == "max_attempts"


async def test_deadline_stops_retries():
    clock = FakeClock()
    clock.now = 0.0
    fn, calls = flaky(10)
    stats = RetryStats()
    policy = RetryPolicy(max_attempts=10, base_delay_s=0.5, max_delay_s=0.5, deadline_s=0.6)
    policy.backoff = lambda n: 0.5  # deterministic: every wait is 0.5 s
    with pytest.raises(RetryableError):
        await call_with_retries(fn, policy, sleep=clock.sleep, clock=clock, stats=stats)
    assert stats.gave_up_reason == "deadline" and calls["n"] == 2


async def test_retry_budget_prevents_retry_storms():
    clock = FakeClock()
    budget = RetryBudget(ratio=0.1, tokens=1.0)
    stats = RetryStats()
    fn, _ = flaky(10)
    with pytest.raises(RetryableError):
        await call_with_retries(fn, RetryPolicy(max_attempts=5), budget, sleep=clock.sleep, clock=clock, stats=stats)
    # 1 initial token + 0.1 deposited = one retry allowed, then the budget is empty
    assert stats.attempts == 2 and stats.gave_up_reason == "budget_exhausted"


async def test_http_client_retries_503_then_succeeds():
    transport = feature_store_transport(fail_first=2)
    store = HttpFeatureStore("http://fs.test", policy=RetryPolicy(max_attempts=3, base_delay_s=0.001), transport=transport)
    feats = await store.get_customer_features("cus_1")
    assert feats == {"txn_count_24h": 3, "avg_amount_30d": 52.0}
    assert transport.calls == 3
    await store.aclose()


async def test_http_client_retries_timeouts():
    transport = feature_store_transport(fail_first=1, timeout=True)
    store = HttpFeatureStore("http://fs.test", policy=RetryPolicy(base_delay_s=0.001), transport=transport)
    assert (await store.get_customer_features("cus_1"))["txn_count_24h"] == 3
    assert transport.calls == 2
    await store.aclose()


async def test_http_client_does_not_retry_4xx():
    transport = feature_store_transport(fail_first=5, status_code=404)
    store = HttpFeatureStore("http://fs.test", policy=RetryPolicy(base_delay_s=0.001), transport=transport)
    with pytest.raises(EnrichmentUnavailable):
        await store.get_customer_features("cus_1")
    assert transport.calls == 1  # a wrong request stays wrong: no retry
    await store.aclose()


async def test_http_client_converts_exhaustion_to_enrichment_unavailable():
    transport = feature_store_transport(fail_first=99)
    store = HttpFeatureStore("http://fs.test", policy=RetryPolicy(max_attempts=3, base_delay_s=0.001), transport=transport)
    with pytest.raises(EnrichmentUnavailable):
        await store.get_customer_features("cus_1")
    assert transport.calls == 3
    await store.aclose()
