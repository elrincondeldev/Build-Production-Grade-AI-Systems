"""Cost-based threshold selection. 📖 See lesson 4.2.

Omar's cost model for one transaction, given a threshold t and a score p:

    flagged (p >= t)  → a reviewer looks at it: costs `review_cost`
                        if it was legit, the customer is annoyed: + `friction_cost`
                        if it was fraud, we stop it: no loss
    not flagged       → if it was fraud, we lose the amount (× `loss_multiplier`)
                        if legit: no cost

Accuracy, F1 and "0.5" know nothing about these euros. The business does.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class CostModel:
    review_cost: float = 5.0  # analyst time per flagged transaction (€)
    friction_cost: float = 3.0  # churn risk / support contact for a false alarm (€)
    loss_multiplier: float = 1.0  # missed fraud costs the amount (chargeback) × this


def expected_cost(
    y_true: np.ndarray, scores: np.ndarray, amounts: np.ndarray, threshold: float, costs: CostModel
) -> float:
    y_true = np.asarray(y_true).astype(bool)
    flagged = np.asarray(scores) >= threshold
    amounts = np.asarray(amounts, dtype=float)
    review = costs.review_cost * flagged.sum()
    friction = costs.friction_cost * (flagged & ~y_true).sum()
    missed = costs.loss_multiplier * amounts[~flagged & y_true].sum()
    return float(review + friction + missed)


def sweep(
    y_true: np.ndarray,
    scores: np.ndarray,
    amounts: np.ndarray,
    costs: CostModel,
    thresholds: np.ndarray | None = None,
) -> pd.DataFrame:
    """Evaluate cost, precision and recall for every candidate threshold."""
    thresholds = np.round(np.linspace(0.01, 0.99, 99), 2) if thresholds is None else thresholds
    y = np.asarray(y_true).astype(bool)
    rows = []
    for t in thresholds:
        flagged = np.asarray(scores) >= t
        tp = int((flagged & y).sum())
        fp = int((flagged & ~y).sum())
        fn = int((~flagged & y).sum())
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        rows.append(
            {
                "threshold": float(t),
                "cost": expected_cost(y, scores, amounts, float(t), costs),
                "flagged": int(flagged.sum()),
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "precision": precision,
                "recall": recall,
                "f1": f1,
            }
        )
    return pd.DataFrame(rows)


def best_threshold(table: pd.DataFrame) -> float:
    """Lowest-cost threshold (ties → the higher threshold, i.e. fewer reviews)."""
    best = table[table["cost"] == table["cost"].min()]
    return float(best["threshold"].max())
