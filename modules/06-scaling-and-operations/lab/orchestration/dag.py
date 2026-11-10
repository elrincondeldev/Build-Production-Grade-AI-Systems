"""A ~100-line workflow engine, so you can see what Airflow/Prefect/Dagster do for you.

📖 Lesson 6.2. Every orchestrator boils down to:
1. tasks with declared dependencies (a DAG: directed acyclic graph),
2. a topological order to run them in,
3. retries, and
4. "if a task fails, skip everything downstream of it".
What real orchestrators add on top: scheduling, distributed workers, a UI,
backfills, persistence of state, alerting, and caching of task results.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


class CycleError(ValueError):
    pass


@dataclass
class TaskSpec:
    name: str
    fn: Callable[[dict[str, Any]], Any]  # receives results of all finished tasks
    upstream: list[str] = field(default_factory=list)
    retries: int = 0
    retry_delay_s: float = 0.0


@dataclass
class TaskRun:
    name: str
    status: str  # success | failed | skipped
    attempts: int = 0
    duration_s: float = 0.0
    error: str | None = None


class DAG:
    def __init__(self, name: str) -> None:
        self.name = name
        self.tasks: dict[str, TaskSpec] = {}

    def task(self, name: str, upstream: list[str] | None = None, retries: int = 0) -> Callable[[Callable], Callable]:
        """Decorator: @dag.task("train", upstream=["validate"])"""

        def register(fn: Callable[[dict[str, Any]], Any]) -> Callable:
            self.add(TaskSpec(name, fn, list(upstream or []), retries))
            return fn

        return register

    def add(self, spec: TaskSpec) -> None:
        if spec.name in self.tasks:
            raise ValueError(f"duplicate task {spec.name!r}")
        self.tasks[spec.name] = spec

    def topological_order(self) -> list[str]:
        """Kahn's algorithm. Ties are broken alphabetically so the order is deterministic."""
        for spec in self.tasks.values():
            for up in spec.upstream:
                if up not in self.tasks:
                    raise ValueError(f"task {spec.name!r} depends on unknown task {up!r}")
        indegree = {n: len(s.upstream) for n, s in self.tasks.items()}
        ready = sorted(n for n, d in indegree.items() if d == 0)
        order: list[str] = []
        while ready:
            current = ready.pop(0)
            order.append(current)
            for name, spec in sorted(self.tasks.items()):
                if current in spec.upstream:
                    indegree[name] -= 1
                    if indegree[name] == 0:
                        ready.append(name)
                        ready.sort()
        if len(order) != len(self.tasks):
            stuck = sorted(set(self.tasks) - set(order))
            raise CycleError(f"cycle detected among {stuck}")
        return order

    def run(self, verbose: bool = False) -> dict[str, TaskRun]:
        results: dict[str, Any] = {}
        runs: dict[str, TaskRun] = {}
        for name in self.topological_order():
            spec = self.tasks[name]
            if any(runs[u].status != "success" for u in spec.upstream):
                runs[name] = TaskRun(name, "skipped")
                if verbose:
                    print(f"  ⏭  {name}: skipped (upstream failed)")
                continue
            run = TaskRun(name, "failed")
            start = time.perf_counter()
            for attempt in range(1, spec.retries + 2):
                run.attempts = attempt
                try:
                    results[name] = spec.fn(results)
                    run.status, run.error = "success", None
                    break
                except Exception as exc:  # orchestrators catch everything and record it
                    run.error = f"{type(exc).__name__}: {exc}"
                    if attempt <= spec.retries and spec.retry_delay_s:
                        time.sleep(spec.retry_delay_s)
            run.duration_s = time.perf_counter() - start
            runs[name] = run
            if verbose:
                icon = "✅" if run.status == "success" else "❌"
                extra = f" ({run.error})" if run.error else ""
                print(f"  {icon} {name}: {run.status} in {run.duration_s:.2f}s, attempts={run.attempts}{extra}")
        self.results = results
        return runs
