"""Drift statistics. 📖 See lesson 4.5.

PSI (Population Stability Index) compares the share of data in each bin:

    PSI = Σ (actual% − expected%) · ln(actual% / expected%)

Rules of thumb used across the credit-risk industry:
    < 0.10  no significant change
    0.10–0.25  moderate shift: investigate
    > 0.25  major shift: act (retrain, recalibrate, or check the pipeline)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

EPS = 1e-6


def psi_from_shares(expected: np.ndarray, actual: np.ndarray) -> float:
    e = np.clip(np.asarray(expected, dtype=float), EPS, None)
    a = np.clip(np.asarray(actual, dtype=float), EPS, None)
    return float(np.sum((a - e) * np.log(a / e)))


def psi_numeric(reference: np.ndarray, current: np.ndarray, n_bins: int = 10) -> float:
    """Bins come from the *reference* quantiles, so each holds ~10% of reference data.

    ⚠️ Low-cardinality features (binary flags, hour of day…) collapse into one or
    two quantile bins and PSI silently reads 0. Treat them as categories instead.
    """
    ref = np.asarray(reference, dtype=float)
    cur = np.asarray(current, dtype=float)
    if len(np.unique(ref)) <= 25:
        return psi_categorical(pd.Series(ref), pd.Series(cur))
    edges = np.unique(np.quantile(ref, np.linspace(0, 1, n_bins + 1)))
    edges[0], edges[-1] = -np.inf, np.inf
    ref_share = np.histogram(ref, edges)[0] / len(ref)
    cur_share = np.histogram(cur, edges)[0] / len(cur)
    return psi_from_shares(ref_share, cur_share)


def psi_categorical(reference: pd.Series, current: pd.Series) -> float:
    cats = sorted(set(reference) | set(current))
    ref_share = reference.value_counts(normalize=True).reindex(cats, fill_value=0).to_numpy()
    cur_share = current.value_counts(normalize=True).reindex(cats, fill_value=0).to_numpy()
    return psi_from_shares(ref_share, cur_share)


def ks_test(reference: np.ndarray, current: np.ndarray) -> tuple[float, float]:
    """Kolmogorov–Smirnov: max distance between the two CDFs, plus a p-value.

    With large samples the p-value is tiny for *any* difference, so judge the
    statistic (effect size), not just p < 0.05.
    """
    result = stats.ks_2samp(reference, current)
    return float(result.statistic), float(result.pvalue)


def psi_label(value: float) -> str:
    if value < 0.10:
        return "stable"
    if value < 0.25:
        return "moderate"
    return "MAJOR"


def centroid_cosine_distance(reference: np.ndarray, current: np.ndarray) -> float:
    """1 − cosine similarity between the mean embedding of two query sets."""
    a = reference.mean(axis=0)
    b = current.mean(axis=0)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(1.0 - (a @ b) / denom) if denom else 1.0
