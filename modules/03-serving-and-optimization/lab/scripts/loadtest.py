"""A small async load generator. 📖 Lesson 3.4.

    uv run python scripts/loadtest.py --concurrency 8 --requests 200
    uv run python scripts/loadtest.py --stream --concurrency 8      # also measures TTFT
    uv run python scripts/loadtest.py --repeat-rate 0.5 --label "exact cache on"

It is a *closed-loop* generator: ``concurrency`` virtual users each send a request,
wait for the answer, and immediately send the next. For production work use a
dedicated tool such as Locust (https://locust.io) or k6, which also support
open-loop (fixed arrival rate) tests; read lesson 3.4 for why that distinction matters.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

from kestrel_serving.config import REPO_ROOT
from kestrel_serving.stats import summarize

GOLDEN = REPO_ROOT / "datasets" / "golden" / "handbook_qa.jsonl"


@dataclass
class Sample:
    ok: bool
    latency_ms: float
    ttft_ms: float | None
    cache: str | None = None


def load_questions(path: Path = GOLDEN) -> list[str]:
    return [json.loads(line)["question"] for line in path.read_text().splitlines() if line.strip()]


def question_stream(questions: list[str], n: int, repeat_rate: float, seed: int) -> list[str]:
    """Mix fresh questions with repeats of earlier ones to control the possible cache hit rate."""
    rng = random.Random(seed)
    asked: list[str] = []
    out: list[str] = []
    fresh = iter(questions * (n // len(questions) + 1))
    for _ in range(n):
        if asked and rng.random() < repeat_rate:
            q = rng.choice(asked)
        else:
            q = f"{next(fresh)} (#{len(asked)})" if len(asked) >= len(questions) else next(fresh)
            asked.append(q)
        out.append(q)
    return out


async def one_request(client: httpx.AsyncClient, question: str, stream: bool) -> Sample:
    start = time.perf_counter()
    try:
        if stream:
            ttft = None
            async with client.stream("POST", "/v1/answer/stream", json={"question": question}) as resp:
                async for chunk in resp.aiter_text():
                    if chunk and ttft is None:
                        ttft = (time.perf_counter() - start) * 1000
                ok = resp.status_code == 200
            return Sample(ok, (time.perf_counter() - start) * 1000, ttft)
        resp = await client.post("/v1/answer", json={"question": question})
        cache = resp.json().get("cache") if resp.status_code == 200 else None
        return Sample(resp.status_code == 200, (time.perf_counter() - start) * 1000, None, cache)
    except httpx.HTTPError:
        return Sample(False, (time.perf_counter() - start) * 1000, None)


async def run_load(
    client: httpx.AsyncClient, questions: list[str], concurrency: int, stream: bool = False
) -> tuple[list[Sample], float]:
    queue: asyncio.Queue[str] = asyncio.Queue()
    for q in questions:
        queue.put_nowait(q)
    samples: list[Sample] = []

    async def user() -> None:
        while not queue.empty():
            samples.append(await one_request(client, queue.get_nowait(), stream))

    start = time.perf_counter()
    await asyncio.gather(*(user() for _ in range(concurrency)))
    return samples, time.perf_counter() - start


def report(samples: list[Sample], wall_s: float, label: str, concurrency: int) -> dict[str, object]:
    ok = [s for s in samples if s.ok]
    lat = summarize([s.latency_ms for s in ok])
    ttfts = [s.ttft_ms for s in ok if s.ttft_ms is not None]
    hits = sum(1 for s in ok if s.cache)
    return {
        "label": label,
        "concurrency": concurrency,
        "requests": len(samples),
        "error_rate": f"{1 - len(ok) / len(samples):.1%}" if samples else "n/a",
        "throughput_rps": round(len(ok) / wall_s, 2) if wall_s else 0.0,
        "p50_ms": round(lat["p50"], 1),
        "p95_ms": round(lat["p95"], 1),
        "p99_ms": round(lat["p99"], 1),
        "ttft_p50_ms": round(summarize(ttfts)["p50"], 1) if ttfts else "-",
        "cache_hit_rate": f"{hits / len(ok):.0%}" if ok else "-",
    }


def append_markdown(row: dict[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("| " + " | ".join(row) + " |\n|" + "---|" * len(row) + "\n")
    with path.open("a") as fh:
        fh.write("| " + " | ".join(str(v) for v in row.values()) + " |\n")


async def main_async(args: argparse.Namespace) -> None:
    questions = question_stream(load_questions(), args.requests, args.repeat_rate, args.seed)
    limits = httpx.Limits(max_connections=args.concurrency)
    async with httpx.AsyncClient(base_url=args.url, timeout=args.timeout, limits=limits) as client:
        await run_load(client, questions[: min(5, len(questions))], 1, args.stream)  # warm-up, not measured
        samples, wall = await run_load(client, questions, args.concurrency, args.stream)
    row = report(samples, wall, args.label, args.concurrency)
    append_markdown(row, args.out)
    width = max(len(k) for k in row)
    for key, value in row.items():
        print(f"{key:<{width}}  {value}")
    print(f"\nappended to {args.out}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--requests", type=int, default=200)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--repeat-rate", type=float, default=0.0, help="fraction of requests that repeat an earlier question")
    parser.add_argument("--stream", action="store_true", help="use the streaming endpoint and measure TTFT")
    parser.add_argument("--label", default="baseline")
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--out", type=Path, default=Path("results/loadtest.md"))
    asyncio.run(main_async(parser.parse_args()))


if __name__ == "__main__":
    main()
