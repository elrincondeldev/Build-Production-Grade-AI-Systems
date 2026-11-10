"""Compare no batching, dynamic batching and continuous batching. 📖 Lessons 3.2 and 3.5.

    uv run python scripts/simulate_batching.py                 # three load levels
    uv run python scripts/simulate_batching.py --rps 2 --max-batch 64
    uv run python scripts/simulate_batching.py --decode-base-ms 10   # a faster GPU

Nothing here runs a model: the simulator replays the *cost structure* of LLM inference
(cheap parallel prefill, expensive memory-bound decode steps) so you can see the
consequences of each scheduling policy in seconds.
"""

from __future__ import annotations

import argparse

from kestrel_serving.sim import CostModel, generate_workload, simulate


def run(rps: float, n: int, max_batch: int, max_wait_ms: float, cost: CostModel, seed: int) -> list[dict]:
    workload = generate_workload(n_requests=n, requests_per_s=rps, seed=seed, output_tokens_median=80)
    rows = []
    for policy, kwargs in [
        ("none", {}),
        ("dynamic", {"max_batch": max_batch, "max_wait_ms": max_wait_ms}),
        ("continuous", {"max_batch": max_batch}),
    ]:
        report = simulate(policy, workload, cost, **kwargs)
        row = report.as_row()
        # A system is "keeping up" if it completes requests about as fast as they arrive.
        row["keeps_up"] = "yes" if report.throughput_requests_per_s >= 0.9 * rps else "NO (queue grows)"
        row["gpu_util"] = f"{min(1.0, report.gpu_busy_ms / report.makespan_ms):.0%}"
        rows.append(row)
    return rows


def to_markdown(rows: list[dict]) -> str:
    headers = list(rows[0])
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(str(r[h]) for h in headers) + " |" for r in rows]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rps", type=float, nargs="*", default=[0.25, 1.5, 3.0], help="offered load(s), requests/s")
    parser.add_argument("--requests", type=int, default=400)
    parser.add_argument("--max-batch", type=int, default=32)
    parser.add_argument("--max-wait-ms", type=float, default=100.0)
    parser.add_argument("--prefill-ms-per-token", type=float, default=CostModel.prefill_ms_per_token)
    parser.add_argument("--decode-base-ms", type=float, default=CostModel.decode_base_ms)
    parser.add_argument("--decode-ms-per-seq", type=float, default=CostModel.decode_ms_per_seq)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    cost = CostModel(args.prefill_ms_per_token, args.decode_base_ms, args.decode_ms_per_seq)
    print(f"Cost model: prefill {cost.prefill_ms_per_token} ms/token, decode step "
          f"{cost.decode_base_ms} ms + {cost.decode_ms_per_seq} ms/sequence  (illustrative numbers)\n")
    for rps in args.rps:
        print(f"### Offered load: {rps} requests/s  ({args.requests} requests)\n")
        print(to_markdown(run(rps, args.requests, args.max_batch, args.max_wait_ms, cost, args.seed)))
        print()


if __name__ == "__main__":
    main()
