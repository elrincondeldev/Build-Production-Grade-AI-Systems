"""Fairness audit for the fraud model: compare error rates across groups.

    uv run --extra governance python scripts/fairness_audit.py

📖 See lesson 5.6. The synthetic data has no protected attributes (that is on
purpose), but `country` is a classic *proxy* for nationality, and false
positives (blocked legitimate payments) are the harm customers feel. So we ask:
is a legitimate customer abroad blocked much more often than one at home, and is
that difference justified by actual fraud rates?
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import make_column_transformer

REPO_ROOT = Path(__file__).resolve().parents[4]
CSV = REPO_ROOT / "datasets" / "fraud" / "transactions.csv"
NUMERIC = ["amount", "hour", "is_online", "country_mismatch", "card_age_days", "txn_count_24h",
           "avg_amount_30d", "device_is_new", "distance_from_home_km"]
CATEGORICAL = ["merchant_category"]
THRESHOLD = 0.10  # flag for review if P(fraud) >= 10%


def main() -> None:
    if not CSV.exists():
        subprocess.run([sys.executable, str(REPO_ROOT / "datasets" / "fraud" / "generate.py")], check=True)
    df = pd.read_csv(CSV)
    X, y = df[NUMERIC + CATEGORICAL], df["is_fraud"]  # note: chargeback_filed is excluded (leakage!)
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.3, stratify=y, random_state=0)
    model = make_pipeline(
        make_column_transformer((StandardScaler(), NUMERIC), (OneHotEncoder(handle_unknown="ignore"), CATEGORICAL)),
        LogisticRegression(max_iter=2000),
    ).fit(X_tr, y_tr)

    test = df.loc[X_te.index].copy()
    test["flagged"] = model.predict_proba(X_te)[:, 1] >= THRESHOLD
    test["group"] = test["country_mismatch"].map({0: "domestic", 1: "abroad"})

    rows = []
    for group, g in test.groupby("group"):
        legit, fraud = g[g.is_fraud == 0], g[g.is_fraud == 1]
        rows.append({
            "group": group,
            "transactions": len(g),
            "fraud_rate": g.is_fraud.mean(),
            "false_positive_rate": legit.flagged.mean(),   # legit customers wrongly blocked
            "true_positive_rate": fraud.flagged.mean() if len(fraud) else float("nan"),  # fraud caught
            "flag_rate": g.flagged.mean(),
        })
    report = pd.DataFrame(rows).set_index("group")
    pd.set_option("display.float_format", "{:.3f}".format)
    pd.set_option("display.width", 120)
    print(report.to_string())
    ratio = report.loc["abroad", "false_positive_rate"] / report.loc["domestic", "false_positive_rate"]
    print(f"\nFPR ratio abroad/domestic: {ratio:.1f}x")
    print("Question for Omar and Priya: is this gap explained by the real fraud-rate gap, "
          "and is it acceptable for the business and the law? Document the answer in the model card.")


if __name__ == "__main__":
    main()
