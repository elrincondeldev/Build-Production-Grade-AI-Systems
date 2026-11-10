import pytest

from kestrel_platform.capacity import (
    ApiPricing,
    CapacityInputs,
    api_monthly_cost,
    breakeven_requests_per_month,
    plan_capacity,
)
from kestrel_platform.costs import build_report, compute_options, load_assumptions

WORKED = CapacityInputs(peak_rps=20, avg_rps=6, input_tokens=800, output_tokens=250)


def test_worked_example_from_lesson_6_3() -> None:
    plan = plan_capacity(WORKED)
    assert plan.gpu_seconds_per_request == pytest.approx(0.14)
    assert plan.busy_replicas_at_peak == pytest.approx(2.8)
    assert plan.replicas_at_peak == 5  # ceil(2.8 / 0.6)
    assert plan.replicas_at_avg == 2  # ceil(0.84 / 0.6) = 2, also the N+1 minimum
    assert plan.monthly_cost_fixed == pytest.approx(5 * 1.2 * 730)
    assert plan.requests_per_month == pytest.approx(6 * 3600 * 730)


def test_float_rounding_does_not_buy_an_extra_gpu() -> None:
    plan = plan_capacity(CapacityInputs(peak_rps=60, avg_rps=18, input_tokens=800, output_tokens=250))
    assert plan.replicas_at_peak == 14  # 8.4 / 0.6 == 14, not 15


def test_min_replicas_floor() -> None:
    plan = plan_capacity(CapacityInputs(peak_rps=0.1, avg_rps=0.05, input_tokens=100, output_tokens=50))
    assert plan.replicas_at_peak == 2


def test_invalid_inputs() -> None:
    with pytest.raises(ValueError):
        CapacityInputs(peak_rps=1, avg_rps=2, input_tokens=1, output_tokens=1)
    with pytest.raises(ValueError):
        CapacityInputs(peak_rps=1, avg_rps=1, input_tokens=1, output_tokens=1, target_utilization=0)


def test_api_cost() -> None:
    cost = api_monthly_cost(1_000_000, 800, 250, ApiPricing(0.15, 0.60))
    assert cost == pytest.approx(270.0)


def test_breakeven_exists_for_expensive_api_and_is_lower_than_for_cheap_api() -> None:
    cheap = breakeven_requests_per_month(WORKED, ApiPricing(0.15, 0.60), 2000)
    pricey = breakeven_requests_per_month(WORKED, ApiPricing(2.5, 10.0), 2000)
    assert pricey is not None and cheap is not None
    assert pricey < cheap


def test_cost_report_renders(lab_dir) -> None:
    a = load_assumptions(lab_dir / "cost_assumptions.toml")
    options = compute_options(a)
    assert {o.kind for o in options} == {"api", "self_host"}
    report = build_report(a)
    assert "# Kestrel platform monthly cost report" in report
    assert "Break-even" in report
