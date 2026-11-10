"""Capacity planning for self-hosted LLM inference, and API-vs-self-host cost.

📖 Lesson 6.3 (capacity) and lesson 3.3 (unit economics).

The model is deliberately simple so you can check every number by hand:

    GPU-seconds per request = input_tokens / prefill_tps + output_tokens / decode_tps

where prefill_tps and decode_tps are the *aggregate* throughputs of ONE replica
when it is serving many requests at once (continuous batching, lesson 3.5).
Measure them with a load test on your own hardware; the defaults are only
illustrative, roughly in the range of a small (~7-8B) model on one mid-range
datacenter GPU.

    busy replicas  = peak_rps * GPU-seconds per request
    replicas       = ceil(busy replicas / target_utilization), at least min_replicas
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

HOURS_PER_MONTH = 730  # 365 * 24 / 12


@dataclass(frozen=True)
class CapacityInputs:
    peak_rps: float
    avg_rps: float
    input_tokens: int
    output_tokens: int
    prefill_tokens_per_s: float = 20_000.0  # per replica, aggregate (illustrative)
    decode_tokens_per_s: float = 2_500.0  # per replica, aggregate (illustrative)
    target_utilization: float = 0.6  # headroom for spikes and failover
    min_replicas: int = 2  # N+1: survive one replica (or zone) failing
    gpu_hourly_cost: float = 1.20  # EUR per replica-hour (illustrative)

    def __post_init__(self) -> None:
        if not 0 < self.target_utilization <= 1:
            raise ValueError("target_utilization must be in (0, 1]")
        if self.avg_rps > self.peak_rps:
            raise ValueError("avg_rps cannot exceed peak_rps")


@dataclass(frozen=True)
class CapacityPlan:
    gpu_seconds_per_request: float
    busy_replicas_at_peak: float
    replicas_at_peak: int
    replicas_at_avg: int
    monthly_cost_fixed: float  # provisioned for peak 24/7
    monthly_cost_autoscaled: float  # rough: average-load replica count 24/7
    requests_per_month: float
    cost_per_1k_requests: float  # using the autoscaled estimate


def _replicas_for(rps: float, gpu_s: float, inputs: CapacityInputs) -> int:
    busy = rps * gpu_s
    # round() first: 8.4 / 0.6 is 14.000000000000002 in floating point, and a
    # naive ceil() would buy a 15th GPU for a rounding error.
    return max(inputs.min_replicas, math.ceil(round(busy / inputs.target_utilization, 9)))


def plan_capacity(inputs: CapacityInputs) -> CapacityPlan:
    gpu_s = inputs.input_tokens / inputs.prefill_tokens_per_s + inputs.output_tokens / inputs.decode_tokens_per_s
    peak = _replicas_for(inputs.peak_rps, gpu_s, inputs)
    avg = _replicas_for(inputs.avg_rps, gpu_s, inputs)
    fixed = peak * inputs.gpu_hourly_cost * HOURS_PER_MONTH
    autoscaled = avg * inputs.gpu_hourly_cost * HOURS_PER_MONTH
    requests = inputs.avg_rps * 3600 * HOURS_PER_MONTH
    return CapacityPlan(
        gpu_seconds_per_request=gpu_s,
        busy_replicas_at_peak=inputs.peak_rps * gpu_s,
        replicas_at_peak=peak,
        replicas_at_avg=avg,
        monthly_cost_fixed=fixed,
        monthly_cost_autoscaled=autoscaled,
        requests_per_month=requests,
        cost_per_1k_requests=autoscaled / requests * 1000 if requests else float("inf"),
    )


@dataclass(frozen=True)
class ApiPricing:
    input_per_million: float  # EUR per 1M input tokens
    output_per_million: float  # EUR per 1M output tokens


def api_monthly_cost(requests_per_month: float, input_tokens: int, output_tokens: int, pricing: ApiPricing) -> float:
    per_request = (input_tokens * pricing.input_per_million + output_tokens * pricing.output_per_million) / 1_000_000
    return requests_per_month * per_request


def self_host_monthly_cost(plan: CapacityPlan, ops_overhead_per_month: float) -> float:
    """GPU cost plus the people cost everyone forgets: on-call, upgrades, capacity work."""
    return plan.monthly_cost_autoscaled + ops_overhead_per_month


def breakeven_requests_per_month(
    inputs: CapacityInputs, pricing: ApiPricing, ops_overhead_per_month: float, max_rps: float = 1_000.0
) -> float | None:
    """Smallest monthly volume at which self-hosting becomes cheaper than the API.

    Self-host cost is a step function (whole replicas), so we scan average RPS
    upwards instead of solving an equation. Returns None if never cheaper below max_rps.
    """
    peak_to_avg = inputs.peak_rps / inputs.avg_rps if inputs.avg_rps else 1.0
    rps = 0.01
    while rps <= max_rps:
        plan = plan_capacity(replace(inputs, avg_rps=rps, peak_rps=rps * peak_to_avg))
        api = api_monthly_cost(plan.requests_per_month, inputs.input_tokens, inputs.output_tokens, pricing)
        if self_host_monthly_cost(plan, ops_overhead_per_month) < api:
            return plan.requests_per_month
        rps *= 1.1
    return None
