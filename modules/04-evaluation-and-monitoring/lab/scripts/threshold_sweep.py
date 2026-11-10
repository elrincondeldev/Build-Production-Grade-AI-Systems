"""Pick the fraud threshold that minimises Omar's expected cost. 📖 Lesson 4.2.

    uv run python scripts/threshold_sweep.py
    uv run python scripts/threshold_sweep.py --review-cost 8 --friction-cost 10

Prints the default (0.5), max-F1 and min-cost thresholds side by side, and
saves artifacts/threshold_sweep.png.
"""

from __future__ import annotations

import argparse

import matplotlib

matplotlib.use("Agg")  # no display needed (CI, servers)
import matplotlib.pyplot as plt

from kestrel_fraud.costs import CostModel, best_threshold, sweep
from kestrel_fraud.data import FEATURES, LABEL

from kestrel_fraud.pipeline import ARTIFACTS, train_or_load


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-cost", type=float, default=5.0, help="€ per flagged transaction")
    parser.add_argument("--friction-cost", type=float, default=3.0, help="extra € per false alarm")
    parser.add_argument("--loss-multiplier", type=float, default=1.0, help="missed fraud costs amount × this")
    parser.add_argument("--rows", type=int, default=50_000)
    args = parser.parse_args()

    costs = CostModel(args.review_cost, args.friction_cost, args.loss_multiplier)
    model, _, test = train_or_load(rows=args.rows)
    scores = model.predict_proba(test[FEATURES])[:, 1]
    table = sweep(test[LABEL].to_numpy(), scores, test["amount"].to_numpy(), costs)

    t_cost = best_threshold(table)
    t_f1 = float(table.loc[table["f1"].idxmax(), "threshold"])
    no_model_cost = float(test.loc[test[LABEL] == 1, "amount"].sum()) * costs.loss_multiplier

    print(f"test set: {len(test):,} transactions, {int(test[LABEL].sum())} fraud "
          f"(€{no_model_cost:,.0f} at risk)\n")
    print(f"{'policy':<22}{'threshold':>10}{'flagged':>9}{'recall':>8}{'precision':>11}{'cost €':>11}")
    for name, t in [("default 0.5", 0.5), ("max F1", t_f1), ("min expected cost", t_cost)]:
        row = table.loc[(table["threshold"] - t).abs().idxmin()]
        print(f"{name:<22}{t:>10.2f}{int(row.flagged):>9}{row.recall:>8.2f}{row.precision:>11.2f}{row.cost:>11,.0f}")
    print(f"{'flag nothing':<22}{'—':>10}{0:>9}{0.0:>8.2f}{'—':>11}{no_model_cost:>11,.0f}")

    ARTIFACTS.mkdir(exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(table["threshold"], table["cost"], label="expected cost (€)")
    ax.axvline(0.5, ls="--", c="grey", label="default 0.5")
    ax.axvline(t_cost, ls="--", c="green", label=f"min cost {t_cost:.2f}")
    ax.set_xlabel("threshold")
    ax.set_ylabel("cost on test set (€)")
    ax.set_title("Kestrel Pay fraud: cost vs threshold")
    ax.legend()
    fig.tight_layout()
    out = ARTIFACTS / "threshold_sweep.png"
    fig.savefig(out, dpi=120)
    print(f"\nsaved {out}")


if __name__ == "__main__":
    main()
