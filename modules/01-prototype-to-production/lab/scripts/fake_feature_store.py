"""A tiny, deliberately unreliable "online feature store" for the retry experiments.

Run it next to the fraud-service:

    uv run python scripts/fake_feature_store.py --port 8101 --fail-rate 0.3 --latency-ms 50

It returns per-customer aggregates and can fail (HTTP 503) or be slow on demand,
so you can watch retries, backoff, the retry budget and graceful degradation in
the fraud-service logs.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import random

import uvicorn
from fastapi import FastAPI, HTTPException, Request


def build_app(fail_rate: float, latency_ms: int, seed: int) -> FastAPI:
    app = FastAPI(title="fake feature store")
    rng = random.Random(seed)

    @app.get("/v1/customers/{customer_id}/features")
    async def features(customer_id: str, request: Request) -> dict[str, float]:
        print(f"feature-store  request_id={request.headers.get('x-request-id')}  customer={customer_id}", flush=True)
        if latency_ms:
            await asyncio.sleep(rng.uniform(0.5, 1.5) * latency_ms / 1000)
        if rng.random() < fail_rate:
            raise HTTPException(status_code=503, detail="injected failure")
        # Deterministic per customer, so repeated calls agree.
        h = int(hashlib.sha256(customer_id.encode()).hexdigest(), 16)
        return {"txn_count_24h": h % 12, "avg_amount_30d": 15 + (h % 9000) / 100}

    return app


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=8101)
    p.add_argument("--fail-rate", type=float, default=0.0)
    p.add_argument("--latency-ms", type=int, default=20)
    p.add_argument("--seed", type=int, default=0)
    a = p.parse_args()
    uvicorn.run(build_app(a.fail_rate, a.latency_ms, a.seed), host="127.0.0.1", port=a.port, log_level="warning")


if __name__ == "__main__":
    main()
