"""Calibration metrics written out by hand so you can see the maths. 📖 Lesson 4.2."""

from __future__ import annotations

import numpy as np


def brier_score(y_true: np.ndarray, probs: np.ndarray) -> float:
    """Mean squared error between predicted probability and the 0/1 outcome.

    0.0 is perfect. Predicting the base rate b for everyone scores b·(1−b)
    (≈ 0.0139 at a 1.4% fraud rate), a useful "no-skill" reference point.
    """
    y = np.asarray(y_true, dtype=float)
    p = np.asarray(probs, dtype=float)
    return float(np.mean((p - y) ** 2))


def expected_calibration_error(y_true: np.ndarray, probs: np.ndarray, n_bins: int = 10) -> float:
    """ECE with equal-frequency bins (better than equal-width when scores are skewed).

    ECE = Σ_bins (bin_size / N) · |mean(predicted) − mean(observed)|
    """
    y = np.asarray(y_true, dtype=float)
    p = np.asarray(probs, dtype=float)
    order = np.argsort(p)
    ece = 0.0
    for idx in np.array_split(order, n_bins):
        if len(idx) == 0:
            continue
        ece += len(idx) / len(p) * abs(p[idx].mean() - y[idx].mean())
    return float(ece)
