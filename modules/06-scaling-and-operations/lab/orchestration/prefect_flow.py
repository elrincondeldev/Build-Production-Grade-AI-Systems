"""The same pipeline as a Prefect flow (optional, lesson 6.2).

    uv sync --extra prefect
    uv run python -m orchestration.prefect_flow

Compare with pipeline.py: the five business functions are reused unchanged.
Prefect adds retries, caching, a UI (`uv run prefect server start`), scheduling
and deployments around them.
"""

from __future__ import annotations

from pathlib import Path

try:
    from prefect import flow, task
except ImportError as exc:  # keep the lab importable without the extra
    raise SystemExit("Prefect is optional: run `uv sync --extra prefect` first.") from exc

from orchestration import pipeline

ingest = task(pipeline.ingest, retries=2, retry_delay_seconds=5)
validate = task(pipeline.validate)
train = task(pipeline.train)
evaluate = task(pipeline.evaluate)
register = task(pipeline.register)


@flow(name="fraud-training", log_prints=True)
def fraud_training(workdir: Path = Path("artifacts/prefect"), rows: int = 20_000, seed: int = 42) -> Path:
    raw = ingest(workdir, rows, seed)
    rows_ = validate(raw)
    trained = train(rows_, seed)
    metrics = evaluate(trained)
    target = register(workdir, trained, metrics, raw)
    print(f"registered {target} with {metrics}")
    return target


if __name__ == "__main__":
    fraud_training()
