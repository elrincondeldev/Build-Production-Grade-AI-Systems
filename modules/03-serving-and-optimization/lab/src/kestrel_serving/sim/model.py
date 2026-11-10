"""Requests, workloads and the GPU cost model used by the simulator."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Request:
    request_id: int
    arrival_ms: float
    prompt_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class CostModel:
    """How long the (imaginary) GPU takes for each kind of work.

    Default numbers are *illustrative*, roughly the shape of a small (1-8B) model on
    one data-centre GPU. Real numbers depend on model, GPU, precision and engine.

    prefill_ms_per_token:  prompt processing; all prompt tokens go through the model in
                           parallel, so the per-token cost is small.
    decode_base_ms:        one decode step must read every weight from GPU memory once,
                           whatever the batch size. This is the memory-bound part.
    decode_ms_per_seq:     extra cost per sequence in the batch for that step
                           (attention over its KV cache, sampling, ...).
    """

    prefill_ms_per_token: float = 0.15
    decode_base_ms: float = 25.0
    decode_ms_per_seq: float = 0.6

    def prefill_ms(self, prompt_tokens: int) -> float:
        return self.prefill_ms_per_token * prompt_tokens

    def decode_step_ms(self, batch_size: int) -> float:
        if batch_size <= 0:
            return 0.0
        return self.decode_base_ms + self.decode_ms_per_seq * batch_size


def generate_workload(
    n_requests: int = 300,
    requests_per_s: float = 8.0,
    seed: int = 7,
    prompt_tokens_mean: int = 600,
    output_tokens_median: int = 120,
) -> list[Request]:
    """Poisson arrivals with RAG-like prompts and long-tailed answer lengths.

    The long tail of output lengths is what hurts static batching: one long answer
    holds the whole batch hostage.
    """
    rng = random.Random(seed)
    t = 0.0
    requests: list[Request] = []
    for i in range(n_requests):
        t += rng.expovariate(requests_per_s) * 1000.0  # inter-arrival time in ms
        prompt = max(50, int(rng.gauss(prompt_tokens_mean, prompt_tokens_mean * 0.3)))
        output = int(min(800, max(8, rng.lognormvariate(math.log(output_tokens_median), 0.8))))
        requests.append(Request(i, t, prompt, output))
    return requests
