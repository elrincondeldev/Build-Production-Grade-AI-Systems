import numpy as np
import pytest

from kestrel_serving.stats import percentile, summarize


@pytest.mark.parametrize("p", [0, 1, 25, 50, 90, 95, 99, 100])
def test_percentile_matches_numpy(p):
    values = list(np.random.default_rng(0).lognormal(4, 1, size=997))
    assert percentile(values, p) == pytest.approx(np.percentile(values, p))


def test_percentile_small_cases():
    assert percentile([5.0], 99) == 5.0
    assert percentile([1, 2, 3, 4], 50) == 2.5


def test_percentile_rejects_bad_input():
    with pytest.raises(ValueError):
        percentile([], 50)
    with pytest.raises(ValueError):
        percentile([1, 2], 101)


def test_mean_hides_the_tail():
    # 98 fast requests and 2 very slow ones: the mean looks fine, p99 does not.
    values = [100.0] * 98 + [5000.0] * 2
    s = summarize(values)
    assert s["p50"] == 100.0
    assert s["mean"] < 300
    assert s["p99"] == 5000.0
