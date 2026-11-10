from kestrel_platform.canary import CanaryPolicy, Decision, WindowMetrics, analyze, percentile, wilson_interval


def lat(n: int, ms: float) -> tuple[float, ...]:
    return tuple(ms + (i % 10) * 0.1 for i in range(n))


BASELINE = WindowMetrics(5000, 10, lat(5000, 20.0))


def test_percentile_nearest_rank() -> None:
    assert percentile(list(range(1, 101)), 95) == 95
    assert percentile([5.0], 99) == 5.0


def test_wilson_interval_contains_point_estimate_and_is_wide_for_small_n() -> None:
    low, high = wilson_interval(1, 40)
    assert low < 1 / 40 < high
    assert high > 0.10  # one error in 40 requests proves very little


def test_healthy_canary_with_enough_traffic_is_promoted() -> None:
    canary = WindowMetrics(1000, 0, lat(1000, 20.5))
    assert analyze(BASELINE, canary).decision is Decision.PROMOTE


def test_low_sample_canary_holds_instead_of_promoting() -> None:
    canary = WindowMetrics(40, 0, lat(40, 20.0))
    result = analyze(BASELINE, canary)
    assert result.decision is Decision.HOLD
    assert any("not enough evidence" in r or "need >=" in r for r in result.reasons)


def test_one_error_in_a_small_sample_holds_not_rollback() -> None:
    canary = WindowMetrics(40, 1, lat(40, 20.0))  # 2.5% observed, but CI includes < 1%
    assert analyze(BASELINE, canary).decision is Decision.HOLD


def test_clearly_bad_canary_rolls_back_fast_even_with_few_requests() -> None:
    canary = WindowMetrics(60, 8, lat(60, 20.0))  # 13% errors: lower bound well above 1%
    assert analyze(BASELINE, canary).decision is Decision.ROLLBACK


def test_latency_regression_over_20_percent_rolls_back() -> None:
    canary = WindowMetrics(1000, 0, lat(1000, 25.0))  # +25% p95
    result = analyze(BASELINE, canary)
    assert result.decision is Decision.ROLLBACK
    assert any(c.name == "p95_latency" and c.decision is Decision.ROLLBACK for c in result.checks)


def test_latency_within_budget_is_fine() -> None:
    canary = WindowMetrics(1000, 0, lat(1000, 23.0))  # +15%
    assert analyze(BASELINE, canary).decision is Decision.PROMOTE


def test_policy_is_configurable() -> None:
    strict = CanaryPolicy(max_error_rate=0.001, min_requests=100)
    canary = WindowMetrics(5000, 25, lat(5000, 20.0))  # 0.5%
    assert analyze(BASELINE, canary, strict).decision is Decision.ROLLBACK
