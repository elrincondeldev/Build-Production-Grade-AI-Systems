"""A tiny, deterministic LLM inference simulator. 📖 Lessons 3.2 and 3.5.

It does not run a model. It models the *cost structure* of one:

* prefill cost grows with the number of prompt tokens (compute-bound, parallel);
* each decode step costs a large fixed amount (reading all the weights from memory)
  plus a small amount per sequence in the batch (memory-bound, sequential).

That cost structure is why batching matters so much for LLMs, and why
*continuous* batching beats static batching. Run ``scripts/simulate_batching.py``.
"""

from kestrel_serving.sim.model import CostModel, Request, generate_workload
from kestrel_serving.sim.schedulers import (
    RequestResult,
    SimulationReport,
    simulate,
    simulate_continuous,
    simulate_dynamic,
    simulate_no_batching,
)

__all__ = [
    "CostModel",
    "Request",
    "RequestResult",
    "SimulationReport",
    "generate_workload",
    "simulate",
    "simulate_continuous",
    "simulate_dynamic",
    "simulate_no_batching",
]
