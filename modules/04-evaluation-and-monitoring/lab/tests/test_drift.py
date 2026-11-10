import numpy as np
import pandas as pd

from kestrel_fraud.drift import (
    centroid_cosine_distance,
    ks_test,
    psi_categorical,
    psi_from_shares,
    psi_label,
    psi_numeric,
)


def test_psi_hand_computed_example():
    expected = np.array([0.5, 0.5])
    actual = np.array([0.7, 0.3])
    by_hand = (0.7 - 0.5) * np.log(0.7 / 0.5) + (0.3 - 0.5) * np.log(0.3 / 0.5)
    assert np.isclose(psi_from_shares(expected, actual), by_hand)  # ≈ 0.169


def test_psi_identical_distributions_is_about_zero():
    rng = np.random.default_rng(0)
    a, b = rng.normal(size=20_000), rng.normal(size=20_000)
    assert psi_numeric(a, b) < 0.01
    assert psi_label(psi_numeric(a, b)) == "stable"


def test_psi_detects_mean_shift():
    rng = np.random.default_rng(0)
    assert psi_numeric(rng.normal(size=20_000), rng.normal(1.0, 1.0, size=20_000)) > 0.25


def test_psi_binary_feature_is_not_silently_zero():
    ref = np.array([0] * 950 + [1] * 50)
    cur = np.array([0] * 800 + [1] * 200)
    assert psi_numeric(ref, cur) > 0.1


def test_psi_categorical_new_category():
    ref = pd.Series(["grocery"] * 90 + ["fuel"] * 10)
    cur = pd.Series(["grocery"] * 60 + ["fuel"] * 10 + ["crypto_exchange"] * 30)
    assert psi_categorical(ref, cur) > 0.25


def test_ks_statistic_bounds():
    stat, p = ks_test(np.arange(100), np.arange(100))
    assert stat == 0 and p == 1.0


def test_centroid_distance():
    a = np.array([[1.0, 0.0], [1.0, 0.0]])
    b = np.array([[0.0, 1.0]])
    assert np.isclose(centroid_cosine_distance(a, a), 0.0)
    assert np.isclose(centroid_cosine_distance(a, b), 1.0)
