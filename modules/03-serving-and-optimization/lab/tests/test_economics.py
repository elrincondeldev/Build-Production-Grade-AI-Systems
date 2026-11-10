import pytest

from kestrel_serving.economics import (
    ApiPricing,
    GpuDeployment,
    Workload,
    api_cost_per_day,
    break_even_requests_per_day,
    gpus_needed,
    self_hosted_cost_per_day,
)

PRICING = ApiPricing(usd_per_m_input=1.0, usd_per_m_output=4.0)
GPU = GpuDeployment(usd_per_gpu_hour=2.0, output_tokens_per_s_per_gpu=1000, utilization=0.5,
                    input_token_weight=0.0, peak_to_average=1.0, min_gpus=1)


def test_api_cost_math():
    w = Workload(requests_per_day=1000, input_tokens_per_request=1000, output_tokens_per_request=250)
    # 1M input tokens * $1 + 0.25M output tokens * $4 = $2/day
    assert api_cost_per_day(w, PRICING) == pytest.approx(2.0)


def test_gpus_needed_rounds_up_and_respects_minimum():
    # usable capacity per GPU = 500 tok/s = 43.2M tokens/day
    assert gpus_needed(Workload(1, 0, 100), GPU) == 1
    assert gpus_needed(Workload(432_000, 0, 100), GPU) == 1  # exactly 43.2M tokens/day
    assert gpus_needed(Workload(432_001, 0, 100), GPU) == 2


def test_self_hosted_is_fixed_cost():
    assert self_hosted_cost_per_day(Workload(1, 0, 100), GPU) == pytest.approx(48.0)
    assert self_hosted_cost_per_day(Workload(400_000, 0, 100), GPU) == pytest.approx(48.0)


def test_break_even_is_where_costs_meet():
    be = break_even_requests_per_day(PRICING, GPU, 0, 100)
    w = Workload(be, 0, 100)
    assert api_cost_per_day(w, PRICING) == pytest.approx(self_hosted_cost_per_day(w, GPU))
    assert be == pytest.approx(48.0 / (100 * 4.0 / 1e6))  # 120,000 requests/day


def test_break_even_none_when_api_is_cheaper_per_token():
    cheap_api = ApiPricing(0.01, 0.01)
    assert break_even_requests_per_day(cheap_api, GPU, 0, 100) is None


def test_ops_overhead_moves_break_even_up():
    with_ops = GpuDeployment(**{**GPU.__dict__, "ops_usd_per_month": 3000})
    assert break_even_requests_per_day(PRICING, with_ops, 0, 100) > break_even_requests_per_day(PRICING, GPU, 0, 100)
