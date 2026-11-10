"""CLI: train your first fraud model.

    uv run train-first-model
    uv run train-first-model --threshold 0.1
    uv run train-first-model --overfitting
"""

from __future__ import annotations

import argparse

from .first_model import (
    Metrics,
    build_baseline,
    build_model,
    evaluate,
    load_transactions,
    overfitting_demo,
    predict_with_threshold,
    split,
)
from .paths import ensure_fraud_data


def _row(name: str, m: Metrics) -> str:
    return (
        f"{name:<28} {m.accuracy:>8.2%} {m.precision:>10.2%} {m.recall:>8.2%}"
        f" {m.true_positives:>6} / {m.frauds_in_test:<5} {m.false_positives:>6}"
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Train your first fraud model (Lab 0).")
    parser.add_argument("--threshold", type=float, default=None, help="extra threshold to compare with 0.5")
    parser.add_argument("--overfitting", action="store_true", help="run the decision-tree overfitting demo")
    args = parser.parse_args(argv)

    path = ensure_fraud_data()
    df = load_transactions(path)
    s = split(df)
    print(f"Loaded {len(df):,} transactions from {path.name}; fraud rate = {df['is_fraud'].mean():.2%}")
    print(f"Train: {len(s.X_train):,} rows · Test: {len(s.X_test):,} rows ({int(s.y_test.sum())} frauds)\n")

    baseline = build_baseline().fit(s.X_train, s.y_train)
    model = build_model().fit(s.X_train, s.y_train)

    header = f"{'model':<28} {'accuracy':>8} {'precision':>10} {'recall':>8} {'caught':>14} {'false alarms':>6}"
    print(header)
    print("-" * len(header))
    print(_row("always 'not fraud'", evaluate(s.y_test, baseline.predict(s.X_test))))
    print(_row("logistic regression @0.50", evaluate(s.y_test, model.predict(s.X_test))))
    if args.threshold is not None:
        preds = predict_with_threshold(model, s.X_test, args.threshold)
        print(_row(f"logistic regression @{args.threshold:.2f}", evaluate(s.y_test, preds)))

    if args.overfitting:
        print("\nOverfitting demo (decision trees):")
        print(f"{'max_depth':>10} {'train recall':>13} {'test recall':>12} {'train prec.':>12} {'test prec.':>11}")
        for r in overfitting_demo(s):
            print(
                f"{str(r['max_depth']):>10} {r['train_recall']:>13.2%} {r['test_recall']:>12.2%}"
                f" {r['train_precision']:>12.2%} {r['test_precision']:>11.2%}"
            )


if __name__ == "__main__":
    main()
