"""Canary analysis: compare a canary against the stable baseline and decide
PROMOTE, HOLD or ROLLBACK.

📖 Lesson 6.4. The rules mirror Kestrel's deployment process
(datasets/handbook/deployment-process.md): roll back if the canary's error rate
rises above 1% or its p95 latency rises more than 20% above the baseline.

The interesting part is *statistics on small samples*. At 5% traffic a canary
may have served only 40 requests. One error out of 40 is a 2.5% error rate, but
it tells you almost nothing. So we use a confidence interval:

* **Fail fast**: if even the *optimistic* (lower) bound of the canary error rate
  is above the threshold, the canary is bad with high confidence -> ROLLBACK now.
* **Pass slow**: only PROMOTE when the *pessimistic* (upper) bound is below the
  threshold *and* we have enough requests.
* Anything in between -> HOLD and collect more traffic.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum


class Decision(str, Enum):
    PROMOTE = "promote"
    HOLD = "hold"
    ROLLBACK = "rollback"


@dataclass(frozen=True)
class WindowMetrics:
    """What one version served during an analysis window."""

    requests: int
    errors: int
    latencies_ms: Sequence[float] = ()

    @property
    def error_rate(self) -> float:
        return self.errors / self.requests if self.requests else 0.0

    @property
    def p95_ms(self) -> float | None:
        return percentile(self.latencies_ms, 95) if self.latencies_ms else None


@dataclass(frozen=True)
class CanaryPolicy:
    max_error_rate: float = 0.01  # absolute: 1% (deployment-process.md)
    max_p95_increase: float = 0.20  # relative to baseline: +20% (deployment-process.md)
    min_requests: int = 200  # below this we never PROMOTE
    min_latency_samples: int = 100  # p95 from fewer samples is noise
    z: float = 1.96  # 95% confidence for the Wilson interval


@dataclass
class CheckResult:
    name: str
    decision: Decision
    detail: str


@dataclass
class CanaryResult:
    decision: Decision
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def reasons(self) -> list[str]:
        return [f"{c.name}: {c.decision.value} ({c.detail})" for c in self.checks]


def percentile(values: Sequence[float], pct: float) -> float:
    """Nearest-rank percentile: the smallest value with at least pct% of data at or below it."""
    if not values:
        raise ValueError("percentile of empty sequence")
    ordered = sorted(values)
    rank = max(1, math.ceil(pct / 100 * len(ordered)))
    return ordered[rank - 1]


def wilson_interval(errors: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion.

    Better than "errors/total ± something" at small n and near 0, which is exactly
    where canaries live (few requests, tiny error rates).
    """
    if total == 0:
        return 0.0, 1.0
    p = errors / total
    denom = 1 + z**2 / total
    centre = (p + z**2 / (2 * total)) / denom
    half = z * math.sqrt(p * (1 - p) / total + z**2 / (4 * total**2)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def check_error_rate(canary: WindowMetrics, policy: CanaryPolicy) -> CheckResult:
    low, high = wilson_interval(canary.errors, canary.requests, policy.z)
    detail = (
        f"canary {canary.errors}/{canary.requests} = {canary.error_rate:.2%}, "
        f"95% CI [{low:.2%}, {high:.2%}], limit {policy.max_error_rate:.2%}"
    )
    if low > policy.max_error_rate:
        return CheckResult("error_rate", Decision.ROLLBACK, detail)
    if high <= policy.max_error_rate and canary.requests >= policy.min_requests:
        return CheckResult("error_rate", Decision.PROMOTE, detail)
    return CheckResult("error_rate", Decision.HOLD, detail + "; not enough evidence yet")


def check_latency(baseline: WindowMetrics, canary: WindowMetrics, policy: CanaryPolicy) -> CheckResult:
    if (
        len(canary.latencies_ms) < policy.min_latency_samples
        or len(baseline.latencies_ms) < policy.min_latency_samples
    ):
        return CheckResult(
            "p95_latency",
            Decision.HOLD,
            f"need >= {policy.min_latency_samples} samples per version "
            f"(baseline {len(baseline.latencies_ms)}, canary {len(canary.latencies_ms)})",
        )
    base_p95, can_p95 = baseline.p95_ms, canary.p95_ms
    assert base_p95 is not None and can_p95 is not None
    limit = base_p95 * (1 + policy.max_p95_increase)
    detail = f"canary p95 {can_p95:.1f} ms vs baseline {base_p95:.1f} ms (limit {limit:.1f} ms)"
    if can_p95 > limit:
        return CheckResult("p95_latency", Decision.ROLLBACK, detail)
    return CheckResult("p95_latency", Decision.PROMOTE, detail)


def analyze(baseline: WindowMetrics, canary: WindowMetrics, policy: CanaryPolicy | None = None) -> CanaryResult:
    """Combine checks: any ROLLBACK wins, then any HOLD, otherwise PROMOTE."""
    policy = policy or CanaryPolicy()
    checks = [check_error_rate(canary, policy), check_latency(baseline, canary, policy)]
    if any(c.decision is Decision.ROLLBACK for c in checks):
        return CanaryResult(Decision.ROLLBACK, checks)
    if any(c.decision is Decision.HOLD for c in checks):
        return CanaryResult(Decision.HOLD, checks)
    return CanaryResult(Decision.PROMOTE, checks)
