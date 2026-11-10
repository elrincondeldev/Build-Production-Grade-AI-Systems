"""API vs self-hosted unit economics. 📖 Lesson 3.3.

The key asymmetry:
* An API is a *variable* cost: you pay per token, zero when idle.
* A GPU is a *fixed* cost per hour: you pay whether it serves 0 or 1,000 tokens/s.
So self-hosting only wins above some volume, and only if you keep the GPUs busy.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

SECONDS_PER_DAY = 86_400


@dataclass(frozen=True)
class ApiPricing:
    usd_per_m_input: float  # price per 1M input (prompt) tokens
    usd_per_m_output: float  # price per 1M output (generated) tokens


@dataclass(frozen=True)
class GpuDeployment:
    usd_per_gpu_hour: float
    output_tokens_per_s_per_gpu: float  # *measured* with your model, engine and batch size
    utilization: float = 0.6  # fraction of peak you can sustain without breaking latency SLOs
    # Prefill is far cheaper per token than decode (lesson 3.2). Count one input token
    # as this fraction of an output token when sizing capacity.
    input_token_weight: float = 0.1
    peak_to_average: float = 2.0  # traffic is not flat: size for the peak hour
    min_gpus: int = 1  # for availability you will usually want >= 2
    ops_usd_per_month: float = 0.0  # engineer time, monitoring, on-call... never zero in reality


@dataclass(frozen=True)
class Workload:
    requests_per_day: float
    input_tokens_per_request: float
    output_tokens_per_request: float

    @property
    def input_tokens_per_day(self) -> float:
        return self.requests_per_day * self.input_tokens_per_request

    @property
    def output_tokens_per_day(self) -> float:
        return self.requests_per_day * self.output_tokens_per_request


def api_cost_per_day(w: Workload, p: ApiPricing) -> float:
    return (w.input_tokens_per_day * p.usd_per_m_input + w.output_tokens_per_day * p.usd_per_m_output) / 1e6


def gpus_needed(w: Workload, g: GpuDeployment) -> int:
    weighted_tokens_per_day = w.output_tokens_per_day + g.input_token_weight * w.input_tokens_per_day
    peak_tokens_per_s = weighted_tokens_per_day / SECONDS_PER_DAY * g.peak_to_average
    usable_per_gpu = g.output_tokens_per_s_per_gpu * g.utilization
    return max(g.min_gpus, math.ceil(peak_tokens_per_s / usable_per_gpu))


def self_hosted_cost_per_day(w: Workload, g: GpuDeployment) -> float:
    return gpus_needed(w, g) * g.usd_per_gpu_hour * 24 + g.ops_usd_per_month / 30


def break_even_requests_per_day(
    p: ApiPricing, g: GpuDeployment, input_tokens_per_request: float, output_tokens_per_request: float,
    max_requests_per_day: float = 1e9,
) -> float | None:
    """Smallest daily request volume at which self-hosting is no more expensive than the API.

    Self-hosted cost is a step function (whole GPUs), API cost is a straight line, so we
    walk the steps: with n GPUs the API line crosses n * cost_per_gpu_day at volume V_n;
    V_n is valid if n GPUs are actually enough to serve V_n.
    Returns None when the API is cheaper at every volume up to ``max_requests_per_day``.
    """
    per_request_api = (input_tokens_per_request * p.usd_per_m_input + output_tokens_per_request * p.usd_per_m_output) / 1e6
    gpu_day = g.usd_per_gpu_hour * 24
    ops_day = g.ops_usd_per_month / 30
    n = g.min_gpus
    while True:
        volume = (n * gpu_day + ops_day) / per_request_api
        if volume > max_requests_per_day:
            return None
        w = Workload(volume, input_tokens_per_request, output_tokens_per_request)
        if gpus_needed(w, g) <= n:
            return volume
        n += 1
