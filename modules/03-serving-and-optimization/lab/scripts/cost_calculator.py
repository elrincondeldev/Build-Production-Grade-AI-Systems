"""API vs self-hosted GPU: what does a day of the docs-assistant cost? 📖 Lesson 3.3.

    uv run python scripts/cost_calculator.py
    uv run python scripts/cost_calculator.py --api-in 0.15 --api-out 0.60  # a cheap small model --gpu-hour 2.0 --gpu-tps 1500

⚠️ ALL DEFAULT PRICES ARE EXAMPLES, NOT QUOTES. Prices change every few months.
Replace them with your provider's current list price and, above all, with the
tokens/s *you measured* for your model on your engine (lab step 7).
"""

from __future__ import annotations

import argparse

from kestrel_serving.economics import (
    ApiPricing,
    GpuDeployment,
    Workload,
    api_cost_per_day,
    break_even_requests_per_day,
    gpus_needed,
    self_hosted_cost_per_day,
)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--in-tokens", type=float, default=1500, help="prompt tokens per request (RAG prompts are long)")
    p.add_argument("--out-tokens", type=float, default=200, help="generated tokens per request")
    p.add_argument("--api-in", type=float, default=1.00, help="EXAMPLE: USD per 1M input tokens (mid-size hosted model)")
    p.add_argument("--api-out", type=float, default=4.00, help="EXAMPLE: USD per 1M output tokens")
    p.add_argument("--gpu-hour", type=float, default=2.00, help="EXAMPLE: USD per GPU-hour (on-demand cloud)")
    p.add_argument("--gpu-tps", type=float, default=1500, help="EXAMPLE: measured output tokens/s per GPU at your batch size")
    p.add_argument("--utilization", type=float, default=0.6)
    p.add_argument("--min-gpus", type=int, default=2, help="2 for basic high availability")
    p.add_argument("--ops-month", type=float, default=3000, help="EXAMPLE: USD/month of engineering + tooling to run it")
    a = p.parse_args()

    pricing = ApiPricing(a.api_in, a.api_out)
    gpu = GpuDeployment(a.gpu_hour, a.gpu_tps, a.utilization, min_gpus=a.min_gpus, ops_usd_per_month=a.ops_month)

    print("| requests/day | API $/day | GPUs | self-hosted $/day | cheaper |\n|---|---|---|---|---|")
    for rpd in (1_000, 10_000, 100_000, 1_000_000, 10_000_000):
        w = Workload(rpd, a.in_tokens, a.out_tokens)
        api, own = api_cost_per_day(w, pricing), self_hosted_cost_per_day(w, gpu)
        print(f"| {rpd:,} | {api:,.2f} | {gpus_needed(w, gpu)} | {own:,.2f} | {'API' if api < own else 'self-host'} |")

    be = break_even_requests_per_day(pricing, gpu, a.in_tokens, a.out_tokens)
    print()
    if be is None:
        print("Break-even: never (the API is cheaper per token than your GPUs at this utilization).")
    else:
        print(f"Break-even: ~{be:,.0f} requests/day (~{be / 86_400:.1f} requests/s on average).")
    print("Cost is only one column. Also weigh: rate limits, data residency, latency SLOs, model choice, and who gets paged.")


if __name__ == "__main__":
    main()
