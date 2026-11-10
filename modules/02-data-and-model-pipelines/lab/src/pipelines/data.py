"""Ingestion step for Track A: produce a raw CSV from the course generator.

In a real company this step would pull from a warehouse table or a Kafka topic.
Here we call the shared generator so every learner gets byte-identical data
for the same (rows, seed, scenario). 📖 Lesson 2.1.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd

from pipelines.paths import data_dir, repo_root


def generate_raw(rows: int = 20_000, seed: int = 42, scenario: str = "baseline", out: Path | None = None) -> Path:
    """Run `datasets/fraud/generate.py` and return the CSV path (cached if it exists)."""
    out = out or data_dir() / f"raw_{scenario}_{rows}_{seed}.csv"
    if out.exists():
        return out
    script = repo_root() / "datasets" / "fraud" / "generate.py"
    subprocess.run(
        [sys.executable, str(script), "--rows", str(rows), "--seed", str(seed), "--scenario", scenario, "--out", str(out)],
        check=True,
        capture_output=True,
    )
    return out


def load_raw(path: Path) -> pd.DataFrame:
    """Read the CSV *without* trusting it: everything is validated next."""
    return pd.read_csv(path)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Generate (or reuse) the raw transactions CSV for this lab")
    parser.add_argument("--rows", type=int, default=20_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--scenario", default="baseline", choices=["baseline", "data_drift", "concept_drift"])
    args = parser.parse_args()
    path = generate_raw(args.rows, args.seed, args.scenario)
    df = load_raw(path)
    print(f"{path}  rows={len(df):,}  fraud_rate={df['is_fraud'].mean():.2%}")


if __name__ == "__main__":
    main()
