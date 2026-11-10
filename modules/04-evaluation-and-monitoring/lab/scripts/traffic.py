"""Send realistic traffic (and thumbs up/down) to a running docs-assistant,
so your Grafana dashboard has something to show. 📖 Lesson 4.4.

    uv run uvicorn kestrel_docs.main:create_app --factory --port 8000   # terminal 1
    uv run python scripts/traffic.py --minutes 5                         # terminal 2
    uv run python scripts/traffic.py --minutes 5 --bad-rate 0.6          # simulate unhappy users
"""

from __future__ import annotations

import argparse
import json
import random
import time

import httpx

from kestrel_docs.config import REPO_ROOT


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--minutes", type=float, default=2.0)
    parser.add_argument("--rps", type=float, default=3.0, help="requests per second")
    parser.add_argument("--bad-rate", type=float, default=0.1, help="share of answers rated 'down'")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    golden = [json.loads(line) for line in (REPO_ROOT / "datasets/golden/handbook_qa.jsonl").read_text().splitlines()]
    deadline = time.time() + args.minutes * 60
    sent = 0
    with httpx.Client(base_url=args.url, timeout=30) as client:
        while time.time() < deadline:
            case = rng.choice(golden)
            resp = client.post("/ask", json={"question": case["question"], "role": case["role"]})
            resp.raise_for_status()
            rating = "down" if rng.random() < args.bad_rate else "up"
            client.post("/feedback", json={"request_id": resp.json()["request_id"], "rating": rating})
            sent += 1
            if sent % 20 == 0:
                print(f"sent {sent} requests")
            time.sleep(1 / args.rps)
    print(f"done: {sent} requests")


if __name__ == "__main__":
    main()
