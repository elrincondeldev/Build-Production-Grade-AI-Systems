import pytest

from kestrel_platform.slo import SLO, budget_consumed_by, burn_rate, error_budget, evaluate_burn_alerts, main

SLO_999 = SLO("availability", 0.999, 30)


def test_error_budget_math() -> None:
    status = error_budget(SLO_999, total_events=10_000_000, bad_events=4_200)
    assert status.allowed_bad == pytest.approx(10_000)
    assert status.consumed == pytest.approx(0.42)
    assert status.remaining == pytest.approx(0.58)
    assert not status.exhausted


def test_budget_exhausted() -> None:
    assert error_budget(SLO_999, 1_000_000, 1_500).exhausted


def test_burn_rate_definition() -> None:
    assert burn_rate(0.001, SLO_999) == pytest.approx(1.0)
    assert burn_rate(0.0144, SLO_999) == pytest.approx(14.4)


def test_fast_burn_consumes_two_percent_per_hour() -> None:
    assert budget_consumed_by(14.4, 1, SLO_999) == pytest.approx(0.02)
    assert budget_consumed_by(6, 6, SLO_999) == pytest.approx(0.05)
    assert budget_consumed_by(1, 72, SLO_999) == pytest.approx(0.10)


def test_page_needs_both_windows() -> None:
    # Long window high but the problem already stopped (short window low): no page.
    assert evaluate_burn_alerts(SLO_999, {"1h": 0.02, "5m": 0.0005}) == []
    # Short spike only: no page either.
    assert evaluate_burn_alerts(SLO_999, {"1h": 0.002, "5m": 0.05}) == []
    fired = evaluate_burn_alerts(SLO_999, {"1h": 0.02, "5m": 0.03})
    assert [a.rule.name for a in fired] == ["fast-burn"]
    assert fired[0].rule.severity == "page"


def test_slow_burn_creates_ticket() -> None:
    fired = evaluate_burn_alerts(SLO_999, {"3d": 0.0012, "6h": 0.0011})
    assert [(a.rule.name, a.rule.severity) for a in fired] == [("slow-burn", "ticket")]


def test_cli_prints_budget(capsys: pytest.CaptureFixture[str]) -> None:
    main(["--objective", "0.999", "--total", "10000000", "--bad", "4200", "--ratio", "1h=0.02", "--ratio", "5m=0.03"])
    out = capsys.readouterr().out
    assert "remaining: 58.0%" in out
    assert "fast-burn" in out
