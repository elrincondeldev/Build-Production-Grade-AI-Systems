import numpy as np
from sklearn.metrics import brier_score_loss

from kestrel_fraud.calibration import brier_score, expected_calibration_error


def test_brier_matches_sklearn():
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, 500)
    p = rng.random(500)
    assert np.isclose(brier_score(y, p), brier_score_loss(y, p))


def test_brier_of_base_rate_is_b_times_one_minus_b():
    y = np.array([1] + [0] * 99)
    assert np.isclose(brier_score(y, np.full(100, 0.01)), 0.01 * 0.99)


def test_ece_near_zero_when_perfectly_calibrated():
    rng = np.random.default_rng(1)
    p = rng.random(200_000)
    y = rng.random(200_000) < p  # outcomes drawn from the predicted probabilities
    assert expected_calibration_error(y, p) < 0.01


def test_ece_large_when_overconfident():
    y = np.array([0, 1] * 500)
    p = np.full(1000, 0.95)  # says 95%, reality is 50%
    assert np.isclose(expected_calibration_error(y, p), 0.45)
