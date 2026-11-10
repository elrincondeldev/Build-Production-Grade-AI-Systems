"""How many GPU replicas does the docs-assistant need? (lesson 6.3)

    uv run python scripts/capacity_plan.py
    uv run python scripts/capacity_plan.py --peak-rps 60 --avg-rps 15 --output-tokens 400
"""

from __future__ import annotations

import argparse

from kestrel_platform.capacity import CapacityInputs, plan_capacity


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--peak-rps", type=float, default=20)
    p.add_argument("--avg-rps", type=float, default=6)
    p.add_argument("--input-tokens", type=int, default=800)
    p.add_argument("--output-tokens", type=int, default=250)
    p.add_argument("--prefill-tps", type=float, default=20_000, help="prefill tokens/s per replica (measure it!)")
    p.add_argument("--decode-tps", type=float, default=2_500, help="aggregate decode tokens/s per replica (measure it!)")
    p.add_argument("--target-util", type=float, default=0.6)
    p.add_argument("--min-replicas", type=int, default=2)
    p.add_argument("--gpu-hourly", type=float, default=1.20)
    a = p.parse_args()

    inputs = CapacityInputs(a.peak_rps, a.avg_rps, a.input_tokens, a.output_tokens, a.prefill_tps,
                            a.decode_tps, a.target_util, a.min_replicas, a.gpu_hourly)
    plan = plan_capacity(inputs)
    print("Capacity plan (illustrative throughput numbers: measure your own)")
    print(f"  GPU-seconds per request : {a.input_tokens}/{a.prefill_tps:,.0f} + {a.output_tokens}/{a.decode_tps:,.0f}"
          f" = {plan.gpu_seconds_per_request:.3f} s")
    print(f"  busy replicas at peak   : {a.peak_rps} rps x {plan.gpu_seconds_per_request:.3f} s = {plan.busy_replicas_at_peak:.2f}")
    print(f"  replicas at peak        : ceil({plan.busy_replicas_at_peak:.2f} / {a.target_util}) = {plan.replicas_at_peak}"
          f"  (min {a.min_replicas} for N+1)")
    print(f"  replicas at average     : {plan.replicas_at_avg}")
    print(f"  monthly cost, fixed     : €{plan.monthly_cost_fixed:,.0f}  (peak capacity 24/7)")
    print(f"  monthly cost, autoscaled: €{plan.monthly_cost_autoscaled:,.0f}  (rough lower bound)")
    print(f"  requests per month      : {plan.requests_per_month:,.0f}")
    print(f"  cost per 1k requests    : €{plan.cost_per_1k_requests:.3f}")


if __name__ == "__main__":
    main()
