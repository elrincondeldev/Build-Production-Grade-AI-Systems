"""Leakage detection. 📖 Lesson 2.2.

Leakage = a feature carries information that will NOT be available at prediction
time (usually because it is created after, or because of, the label).

Two complementary checks:
1. **Contract check** (cheap, deterministic): every feature must be declared
   `available="at_decision"` in the schema. Anything else is rejected.
2. **Statistical check** (catches what the contract missed): a single feature
   that on its own separates the classes almost perfectly is suspicious.
   Real fraud signals are weak individually; a single-feature ROC-AUC above
   ~0.9 deserves a human look before it goes anywhere near training.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from pipelines.validate import SCHEMA_BY_NAME


@dataclass(frozen=True)
class LeakageFinding:
    feature: str
    reason: str
    auc: float | None = None


def contract_check(features: list[str]) -> list[LeakageFinding]:
    findings = []
    for f in features:
        col = SCHEMA_BY_NAME.get(f)
        if col is None:
            findings.append(LeakageFinding(f, "not declared in schema: unknown availability"))
        elif col.available != "at_decision":
            findings.append(LeakageFinding(f, f"declared available='{col.available}', not known at decision time"))
    return findings


def single_feature_auc(x: pd.Series, y: pd.Series) -> float:
    """ROC-AUC of one feature used alone as a score, direction-agnostic (0.5 = useless, 1.0 = perfect).

    Categorical features are target-encoded first (mean label per category).
    That in-sample encoding slightly *overestimates* AUC, which is fine for a
    smoke alarm: we want false alarms, not misses.
    """
    if not pd.api.types.is_numeric_dtype(x):
        x = x.astype(str).map(y.groupby(x.astype(str)).mean())
    x = pd.to_numeric(x, errors="coerce").astype("float64")
    x = x.fillna(x.median())
    if x.nunique() < 2 or y.nunique() < 2:
        return 0.5
    auc = roc_auc_score(y, x)
    return float(max(auc, 1 - auc))


def statistical_check(df: pd.DataFrame, label: str, features: list[str], threshold: float = 0.9) -> list[LeakageFinding]:
    y = df[label]
    findings = []
    for f in features:
        auc = single_feature_auc(df[f], y)
        if auc >= threshold:
            findings.append(LeakageFinding(f, f"single-feature ROC-AUC {auc:.3f} ≥ {threshold}: too good to be true", auc))
    return findings


def scan(df: pd.DataFrame, label: str = "is_fraud", threshold: float = 0.9) -> pd.DataFrame:
    """Single-feature AUC for every non-identifier column, sorted. Handy for eyeballing."""
    cols = [c for c in df.columns if c != label and SCHEMA_BY_NAME.get(c) and SCHEMA_BY_NAME[c].available != "identifier"]
    rows = [{"feature": c, "auc": single_feature_auc(df[c], df[label])} for c in cols]
    out = pd.DataFrame(rows).sort_values("auc", ascending=False).reset_index(drop=True)
    out["suspicious"] = out["auc"] >= threshold
    out["declared"] = [SCHEMA_BY_NAME[c].available for c in out["feature"]]
    return out


class LeakageError(Exception):
    pass


def assert_no_leakage(df: pd.DataFrame, features: list[str], label: str = "is_fraud", threshold: float = 0.9) -> None:
    findings = contract_check(features) + statistical_check(df, label, features, threshold)
    if findings:
        raise LeakageError("Leakage suspected:\n" + "\n".join(f"  - {f.feature}: {f.reason}" for f in findings))


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan a transactions CSV for leaky features")
    parser.add_argument("csv", type=Path)
    parser.add_argument("--threshold", type=float, default=0.9)
    args = parser.parse_args()
    df = pd.read_csv(args.csv)
    with pd.option_context("display.width", 120):
        print(scan(df, threshold=args.threshold).to_string(index=False, float_format=lambda v: f"{v:.3f}"))


if __name__ == "__main__":
    np.seterr(all="ignore")
    main()
