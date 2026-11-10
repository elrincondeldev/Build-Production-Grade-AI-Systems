"""Train once, cache the model: shared by the Track A scripts."""

from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd
from sklearn.pipeline import Pipeline

from kestrel_fraud.data import load_transactions, time_split
from kestrel_fraud.model import train

LAB_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS = LAB_DIR / "artifacts"


def train_or_load(rows: int = 50_000, seed: int = 42) -> tuple[Pipeline, pd.DataFrame, pd.DataFrame]:
    """Return (model, train_df, test_df). The model is cached in artifacts/."""
    df = load_transactions("baseline", rows=rows, seed=seed)
    train_df, test_df = time_split(df)
    path = ARTIFACTS / f"fraud_model_rows{rows}_seed{seed}.joblib"
    if path.exists():
        model = joblib.load(path)
    else:
        model = train(train_df)
        ARTIFACTS.mkdir(exist_ok=True)
        joblib.dump(model, path)
    return model, train_df, test_df
