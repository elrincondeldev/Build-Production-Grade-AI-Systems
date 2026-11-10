"""Find shared course data no matter where you run the lab from.

📖 See lesson 0.2: production code never hard-codes absolute paths like
"/Users/sam/Desktop/data.csv". It resolves paths from a known anchor (the repo
root) or from configuration (an environment variable).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def repo_root(start: Path | None = None) -> Path:
    """Walk up from this file until we find the course's `datasets/` folder."""
    here = (start or Path(__file__)).resolve()
    for candidate in [here, *here.parents]:
        if (candidate / "datasets" / "fraud" / "generate.py").exists():
            return candidate
    raise FileNotFoundError(
        "Could not find the course repo root (a folder containing datasets/fraud/generate.py). "
        "Run the lab from inside the cloned repository, or set KESTREL_DATA_DIR."
    )


def data_dir() -> Path:
    """`datasets/` folder. Override with KESTREL_DATA_DIR (12-factor config, see Module 1)."""
    override = os.environ.get("KESTREL_DATA_DIR")
    return Path(override).resolve() if override else repo_root() / "datasets"


def handbook_dir() -> Path:
    return data_dir() / "handbook"


def fraud_csv(scenario: str = "baseline") -> Path:
    name = "transactions.csv" if scenario == "baseline" else f"transactions_{scenario}.csv"
    return data_dir() / "fraud" / name


def ensure_fraud_data(
    out: Path | None = None, rows: int = 50_000, seed: int = 42, scenario: str = "baseline"
) -> Path:
    """Generate the synthetic fraud CSV if it does not exist yet.

    We *call* the shared generator instead of copying it, so every module sees
    exactly the same data for the same seed (reproducibility, see lesson 2.6).
    """
    out = out or fraud_csv(scenario)
    if out.exists():
        return out
    generator = data_dir() / "fraud" / "generate.py"
    subprocess.run(
        [
            sys.executable,
            str(generator),
            "--rows",
            str(rows),
            "--seed",
            str(seed),
            "--scenario",
            scenario,
            "--out",
            str(out),
        ],
        check=True,
    )
    return out
