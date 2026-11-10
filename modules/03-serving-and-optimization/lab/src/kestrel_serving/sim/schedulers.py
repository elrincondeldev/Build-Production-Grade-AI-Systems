"""Three batching policies, simulated step by step.

* no batching ........ one request at a time (what a naive Flask + model.generate() does)
* dynamic batching ... wait up to ``max_wait_ms`` to fill a batch of ``max_batch``, then run
                       the batch to completion; with a huge max_wait this is static batching.
* continuous batching  re-forms the batch at *every decode step*: finished sequences leave,
                       waiting requests join (vLLM, SGLang, TGI, TensorRT-LLM all do this).
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Literal

from kestrel_serving.sim.model import CostModel, Request
from kestrel_serving.stats import percentile

Policy = Literal["none", "dynamic", "continuous"]


@dataclass
class RequestResult:
    request: Request
    first_token_ms: float  # absolute time the first output token was produced
    finish_ms: float  # absolute time the response was returned to the client

    @property
    def latency_ms(self) -> float:
        return self.finish_ms - self.request.arrival_ms

    @property
    def ttft_ms(self) -> float:
        return self.first_token_ms - self.request.arrival_ms


@dataclass
class SimulationReport:
    policy: str
    results: list[RequestResult] = field(default_factory=list)
    gpu_busy_ms: float = 0.0

    @property
    def makespan_ms(self) -> float:
        start = min(r.request.arrival_ms for r in self.results)
        end = max(r.finish_ms for r in self.results)
        return end - start

    @property
    def throughput_tokens_per_s(self) -> float:
        tokens = sum(r.request.output_tokens for r in self.results)
        return tokens / (self.makespan_ms / 1000.0)

    @property
    def throughput_requests_per_s(self) -> float:
        return len(self.results) / (self.makespan_ms / 1000.0)

    def latency(self, p: float) -> float:
        return percentile([r.latency_ms for r in self.results], p)

    def ttft(self, p: float) -> float:
        return percentile([r.ttft_ms for r in self.results], p)

    def as_row(self) -> dict[str, float | str]:
        return {
            "policy": self.policy,
            "throughput_tok_s": round(self.throughput_tokens_per_s, 1),
            "throughput_req_s": round(self.throughput_requests_per_s, 2),
            "latency_p50_ms": round(self.latency(50)),
            "latency_p95_ms": round(self.latency(95)),
            "ttft_p50_ms": round(self.ttft(50)),
            "ttft_p95_ms": round(self.ttft(95)),
        }


def simulate_dynamic(
    requests: list[Request], cost: CostModel, max_batch: int = 16, max_wait_ms: float = 50.0
) -> SimulationReport:
    """Collect a batch (full, or max_wait elapsed), run it until its *longest* answer ends.

    Every sequence in the batch pays for decode steps until the slowest one is done
    (finished sequences are just padding), and responses are returned together.
    """
    report = SimulationReport(policy=f"dynamic(max_batch={max_batch}, max_wait={max_wait_ms:g}ms)")
    pending = deque(sorted(requests, key=lambda r: r.arrival_ms))
    t = 0.0
    while pending:
        first = pending[0]
        t = max(t, first.arrival_ms)
        # The batch closes when it is full or when the oldest request has waited max_wait_ms.
        deadline = max(t, first.arrival_ms + max_wait_ms)
        arrived = [r for r in pending if r.arrival_ms <= deadline]
        if len(arrived) >= max_batch:
            batch = arrived[:max_batch]
            t = max(t, batch[-1].arrival_ms)  # closed as soon as the last slot filled
        else:
            batch = arrived
            t = deadline
        for _ in batch:
            pending.popleft()

        prefill = sum(cost.prefill_ms(r.prompt_tokens) for r in batch)
        t += prefill
        report.gpu_busy_ms += prefill
        first_token_at = None
        for _ in range(max(r.output_tokens for r in batch)):
            step = cost.decode_step_ms(len(batch))  # padded: batch size never shrinks
            t += step
            report.gpu_busy_ms += step
            first_token_at = first_token_at or t
        for r in batch:
            report.results.append(RequestResult(r, first_token_ms=first_token_at, finish_ms=t))
    return report


def simulate_no_batching(requests: list[Request], cost: CostModel) -> SimulationReport:
    """One request at a time, first come first served."""
    report = simulate_dynamic(requests, cost, max_batch=1, max_wait_ms=0.0)
    report.policy = "no batching"
    return report


@dataclass
class _Running:
    request: Request
    generated: int = 0
    first_token_ms: float | None = None


def simulate_continuous(requests: list[Request], cost: CostModel, max_batch: int = 16) -> SimulationReport:
    """Iteration-level scheduling: the batch is rebuilt before every decode step.

    New requests are prefilled in the same iteration they join (a simplification of
    chunked prefill), and a request leaves the batch the moment it emits its last token.
    """
    report = SimulationReport(policy=f"continuous(max_batch={max_batch})")
    waiting: deque[Request] = deque()
    incoming = deque(sorted(requests, key=lambda r: r.arrival_ms))
    running: list[_Running] = []
    t = 0.0
    while incoming or waiting or running:
        while incoming and incoming[0].arrival_ms <= t:
            waiting.append(incoming.popleft())
        if not running and not waiting:
            t = incoming[0].arrival_ms  # GPU idle: jump to the next arrival
            continue

        step_ms = 0.0
        while waiting and len(running) < max_batch:  # admit into free slots
            r = waiting.popleft()
            step_ms += cost.prefill_ms(r.prompt_tokens)
            running.append(_Running(r))
        step_ms += cost.decode_step_ms(len(running))
        t += step_ms
        report.gpu_busy_ms += step_ms

        still_running: list[_Running] = []
        for s in running:
            s.generated += 1
            if s.first_token_ms is None:
                s.first_token_ms = t
            if s.generated >= s.request.output_tokens:
                report.results.append(RequestResult(s.request, s.first_token_ms, finish_ms=t))
            else:
                still_running.append(s)
        running = still_running
    return report


def simulate(
    policy: Policy, requests: list[Request], cost: CostModel | None = None, **kwargs: float
) -> SimulationReport:
    cost = cost or CostModel()
    if policy == "none":
        return simulate_no_batching(requests, cost)
    if policy == "dynamic":
        return simulate_dynamic(requests, cost, **kwargs)  # type: ignore[arg-type]
    if policy == "continuous":
        return simulate_continuous(requests, cost, **kwargs)  # type: ignore[arg-type]
    raise ValueError(f"unknown policy {policy!r}")
