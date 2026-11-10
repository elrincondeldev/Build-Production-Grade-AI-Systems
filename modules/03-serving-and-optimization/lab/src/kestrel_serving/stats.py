"""Latency statistics. 📖 Lesson 3.4.

We implement percentiles ourselves (instead of only calling numpy) so you can see
there is no magic: sort, find the fractional rank, interpolate.
"""

from __future__ import annotations

import math
from collections.abc import Sequence


def percentile(values: Sequence[float], p: float) -> float:
    """Return the p-th percentile (0-100) with linear interpolation.

    Matches ``numpy.percentile(values, p)`` (the default "linear" method).
    """
    if not values:
        raise ValueError("percentile() of an empty sequence")
    if not 0 <= p <= 100:
        raise ValueError("p must be between 0 and 100")
    ordered = sorted(values)
    rank = (len(ordered) - 1) * p / 100  # fractional index into the sorted list
    lo, hi = math.floor(rank), math.ceil(rank)
    if lo == hi:
        return float(ordered[lo])
    weight = rank - lo
    return float(ordered[lo] * (1 - weight) + ordered[hi] * weight)


def summarize(values: Sequence[float]) -> dict[str, float]:
    """The numbers you should report for any latency distribution."""
    if not values:
        return {"count": 0, "mean": 0.0, "p50": 0.0, "p95": 0.0, "p99": 0.0, "max": 0.0}
    return {
        "count": float(len(values)),
        "mean": sum(values) / len(values),
        "p50": percentile(values, 50),
        "p95": percentile(values, 95),
        "p99": percentile(values, 99),
        "max": float(max(values)),
    }
