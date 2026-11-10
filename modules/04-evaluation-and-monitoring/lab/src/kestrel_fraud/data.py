"""Load the synthetic Kestrel Pay transactions by calling the shared generator.

We import ``datasets/fraud/generate.py`` instead of copying it, so every module
uses exactly the same data-generating process (one source of truth).
"""

from __future__ import annotations

import importlib.util
import os
import sys
from dataclasses import asdict
from functools import lru_cache
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[5]
GENERATOR = Path(os.environ.get("KESTREL_DATA_DIR", REPO_ROOT / "datasets")) / "fraud" / "generate.py"

NUMERIC_FEATURES = [
    "amount",
    "hour",
    "is_online",
    "country_mismatch",
    "card_age_days",
    "txn_count_24h",
    "avg_amount_30d",
    "device_is_new",
    "distance_from_home_km",
]
CATEGORICAL_FEATURES = ["merchant_category"]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES
LABEL = "is_fraud"
# Never a feature: `chargeback_filed` is only known after the label (lesson 2.2).
LEAKY_COLUMNS = ["chargeback_filed"]


@lru_cache(maxsize=1)
def _generator_module():
    spec = importlib.util.spec_from_file_location("kestrel_fraud_generate", GENERATOR)
    if spec is None or spec.loader is None:
        raise FileNotFoundError(f"Cannot find the data generator at {GENERATOR}")
    module = importlib.util.module_from_spec(spec)
    # Register before executing: dataclasses look the module up in sys.modules.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_transactions(scenario: str = "baseline", rows: int = 50_000, seed: int = 42) -> pd.DataFrame:
    """Generate transactions in memory (about 1–2 s for 50k rows)."""
    gen = _generator_module()
    df = pd.DataFrame([asdict(t) for t in gen.generate(rows, seed, scenario)])
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def time_split(df: pd.DataFrame, train_frac: float = 0.7) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split by time, not at random: in production you always predict the future."""
    df = df.sort_values("timestamp").reset_index(drop=True)
    cut = int(len(df) * train_frac)
    return df.iloc[:cut], df.iloc[cut:]
