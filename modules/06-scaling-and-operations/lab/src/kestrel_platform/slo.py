"""SLOs, error budgets and multi-window burn-rate alerts.

📖 Lesson 6.4. Follows the approach in the Google SRE Workbook chapter
"Alerting on SLOs": alert on how fast you are *burning* the error budget, and
require both a long and a short window to agree (the long window proves it is
significant, the short window proves it is still happening).

CLI:
    uv run python -m kestrel_platform.slo --objective 0.999 --total 10000000 --bad 4200
    uv run python -m kestrel_platform.slo --objective 0.999 --ratio 1h=0.02 --ratio 5m=0.03
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass


@dataclass(frozen=True)
class SLO:
    name: str
    objective: float  # e.g. 0.999 -> 99.9% of events must be good
    window_days: int = 30

    @property
    def error_budget_ratio(self) -> float:
        """The fraction of events allowed to be bad: 1 - objective."""
        return 1 - self.objective

    @property
    def window_hours(self) -> int:
        return self.window_days * 24


@dataclass(frozen=True)
class BudgetStatus:
    allowed_bad: float
    bad: int
    consumed: float  # fraction of budget used, can exceed 1.0
    remaining: float  # fraction left, negative when overspent

    @property
    def exhausted(self) -> bool:
        return self.remaining <= 0


def error_budget(slo: SLO, total_events: int, bad_events: int) -> BudgetStatus:
    allowed = slo.error_budget_ratio * total_events
    consumed = bad_events / allowed if allowed else float("inf")
    return BudgetStatus(allowed_bad=allowed, bad=bad_events, consumed=consumed, remaining=1 - consumed)


def burn_rate(error_ratio: float, slo: SLO) -> float:
    """How many times faster than "exactly on budget" you are failing.

    burn rate 1  -> you will use exactly 100% of the budget by the end of the window.
    burn rate 14.4 over 1 hour -> 14.4 * 1h / 720h = 2% of a 30-day budget gone in an hour.
    """
    return error_ratio / slo.error_budget_ratio


def budget_consumed_by(burn: float, hours: float, slo: SLO) -> float:
    """Fraction of the whole window's budget a given burn rate eats in `hours`."""
    return burn * hours / slo.window_hours


@dataclass(frozen=True)
class BurnRateRule:
    name: str
    long_window: str  # label such as "1h"
    short_window: str  # label such as "5m"
    threshold: float
    severity: str  # page | ticket


# The classic multi-window, multi-burn-rate set for a 30-day SLO.
DEFAULT_RULES: tuple[BurnRateRule, ...] = (
    BurnRateRule("fast-burn", "1h", "5m", 14.4, "page"),  # 2% of budget in 1h
    BurnRateRule("medium-burn", "6h", "30m", 6.0, "page"),  # 5% of budget in 6h
    BurnRateRule("slow-burn", "3d", "6h", 1.0, "ticket"),  # 10% of budget in 3 days
)


@dataclass(frozen=True)
class FiredAlert:
    rule: BurnRateRule
    long_burn: float
    short_burn: float


def evaluate_burn_alerts(
    slo: SLO, error_ratios: dict[str, float], rules: tuple[BurnRateRule, ...] = DEFAULT_RULES
) -> list[FiredAlert]:
    """Fire a rule only if BOTH its long and short windows exceed the threshold.

    `error_ratios` maps window labels ("5m", "1h", "6h", ...) to bad/total over that window.
    Missing windows are treated as 0 (no evidence -> no alert).
    """
    fired: list[FiredAlert] = []
    for rule in rules:
        long_burn = burn_rate(error_ratios.get(rule.long_window, 0.0), slo)
        short_burn = burn_rate(error_ratios.get(rule.short_window, 0.0), slo)
        if long_burn >= rule.threshold and short_burn >= rule.threshold:
            fired.append(FiredAlert(rule, long_burn, short_burn))
    return fired


def _parse_ratio(text: str) -> tuple[str, float]:
    window, _, value = text.partition("=")
    return window.strip(), float(value)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Error budget and burn-rate calculator")
    parser.add_argument("--name", default="fraud-service availability")
    parser.add_argument("--objective", type=float, default=0.999)
    parser.add_argument("--window-days", type=int, default=30)
    parser.add_argument("--total", type=int, help="total events so far in the window")
    parser.add_argument("--bad", type=int, help="bad events so far in the window")
    parser.add_argument("--ratio", action="append", default=[], type=_parse_ratio, help="window=error_ratio, e.g. 1h=0.02")
    args = parser.parse_args(argv)

    slo = SLO(args.name, args.objective, args.window_days)
    print(f"SLO: {slo.name}  objective {slo.objective:.3%} over {slo.window_days} days")
    print(f"Error budget: {slo.error_budget_ratio:.3%} of events "
          f"(= {slo.error_budget_ratio * slo.window_hours * 60:.1f} fully-down minutes)")
    if args.total is not None and args.bad is not None:
        status = error_budget(slo, args.total, args.bad)
        print(f"Allowed bad events: {status.allowed_bad:,.0f}   actual: {status.bad:,}")
        print(f"Budget consumed: {status.consumed:.1%}   remaining: {status.remaining:.1%}"
              + ("   ⛔ EXHAUSTED: freeze risky releases" if status.exhausted else ""))
    if args.ratio:
        ratios = dict(args.ratio)
        for window, ratio in ratios.items():
            print(f"  burn rate over {window:>4}: {burn_rate(ratio, slo):6.1f}x")
        fired = evaluate_burn_alerts(slo, ratios)
        if not fired:
            print("No burn-rate alert fires.")
        for alert in fired:
            print(f"🔔 {alert.rule.severity.upper()}: {alert.rule.name} "
                  f"({alert.rule.long_window} {alert.long_burn:.1f}x and {alert.rule.short_window} {alert.short_burn:.1f}x "
                  f">= {alert.rule.threshold}x)")


if __name__ == "__main__":
    main()
