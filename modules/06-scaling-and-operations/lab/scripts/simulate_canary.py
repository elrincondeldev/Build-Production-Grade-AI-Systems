"""Simulate a canary release: stable v1 vs canary v2, traffic shifted 5% -> 25% -> 100%.

By default both versions run in-process (FastAPI TestClient), so no servers or
cluster are needed. The canary analysis (src/kestrel_platform/canary.py) runs
after every batch of requests, just like an Argo Rollouts AnalysisRun polls
Prometheus every interval.

    uv run python scripts/simulate_canary.py --fault none      # healthy canary -> promoted
    uv run python scripts/simulate_canary.py --fault errors    # 5% errors     -> rollback
    uv run python scripts/simulate_canary.py --fault latency   # +40 ms        -> rollback

Against real servers (start two uvicorn processes first, see lab README step 4):
    uv run python scripts/simulate_canary.py --stable-url http://localhost:8080 --canary-url http://localhost:8081
"""

from __future__ import annotations

import argparse
import random
import sys
import time
from collections.abc import Callable

from kestrel_platform.canary import CanaryPolicy, Decision, WindowMetrics, analyze

PAYLOAD = {"amount": 42.0, "merchant_category": "online_retail", "hour": 14, "is_online": True}
WEIGHTS = (5, 25, 100)


class Recorder:
    def __init__(self) -> None:
        self.requests = 0
        self.errors = 0
        self.latencies_ms: list[float] = []

    def snapshot(self) -> WindowMetrics:
        return WindowMetrics(self.requests, self.errors, tuple(self.latencies_ms))


def in_process_senders(fault: str) -> tuple[Callable[[], int], Callable[[], int]]:
    import warnings

    with warnings.catch_warnings():  # silence an upstream deprecation notice in the demo output
        warnings.simplefilter("ignore")
        from fastapi.testclient import TestClient

    from kestrel_platform.config import Settings
    from kestrel_platform.main import create_app

    canary_settings = {
        "none": {},
        "errors": {"fault_error_rate": 0.05},
        "latency": {"fault_extra_latency_ms": 40.0},
    }[fault]
    stable = TestClient(create_app(Settings(app_version="v1")))
    canary = TestClient(create_app(Settings(app_version="v2", fault_seed=7, **canary_settings)))
    return (lambda: stable.post("/v1/score", json=PAYLOAD).status_code,
            lambda: canary.post("/v1/score", json=PAYLOAD).status_code)


def http_senders(stable_url: str, canary_url: str) -> tuple[Callable[[], int], Callable[[], int]]:
    import httpx

    client = httpx.Client(timeout=5.0)

    def sender(url: str) -> Callable[[], int]:
        def send() -> int:
            try:
                return client.post(f"{url}/v1/score", json=PAYLOAD).status_code
            except httpx.HTTPError:
                return 599  # a timeout or connection error counts as a failure
        return send

    return sender(stable_url), sender(canary_url)


def run(send_stable: Callable[[], int], send_canary: Callable[[], int], requests_per_step: int, batch: int, seed: int) -> Decision:
    rng = random.Random(seed)
    stable, canary = Recorder(), Recorder()
    policy = CanaryPolicy()
    for weight in WEIGHTS:
        print(f"\n▶ setWeight {weight}%  (canary gets ~{weight}% of traffic)")
        sent = 0
        result = None
        while sent < requests_per_step:
            for _ in range(batch):
                to_canary = rng.random() < weight / 100
                recorder, send = (canary, send_canary) if to_canary else (stable, send_stable)
                start = time.perf_counter()
                status = send()
                recorder.latencies_ms.append((time.perf_counter() - start) * 1000)
                recorder.requests += 1
                recorder.errors += int(status >= 500)
            sent += batch
            result = analyze(stable.snapshot(), canary.snapshot(), policy)
            print(f"  analysis after {sent:>5} requests: {result.decision.value.upper():8} "
                  f"| canary {canary.requests} req, {canary.errors} err")
            if result.decision is Decision.ROLLBACK:
                print("\n⛔ AUTOMATIC ROLLBACK: all traffic back to stable v1")
                for reason in result.reasons:
                    print(f"   - {reason}")
                return Decision.ROLLBACK
        assert result is not None
        if weight == 100:
            if result.decision is Decision.PROMOTE:
                print("\n✅ PROMOTED: canary v2 is the new stable")
                for reason in result.reasons:
                    print(f"   - {reason}")
            else:
                print("\n⏸  PAUSED: not enough evidence to promote; a human must decide")
            return result.decision
        print(f"  step complete: no failure detected at {weight}%, advancing")
    return Decision.HOLD


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fault", choices=["none", "errors", "latency"], default="errors")
    parser.add_argument("--requests-per-step", type=int, default=1000)
    parser.add_argument("--batch", type=int, default=100)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--stable-url")
    parser.add_argument("--canary-url")
    args = parser.parse_args()
    if args.stable_url and args.canary_url:
        senders = http_senders(args.stable_url, args.canary_url)
    else:
        senders = in_process_senders(args.fault)
    decision = run(*senders, requests_per_step=args.requests_per_step, batch=args.batch, seed=args.seed)
    sys.exit(0 if decision is Decision.PROMOTE else 1)


if __name__ == "__main__":
    main()
