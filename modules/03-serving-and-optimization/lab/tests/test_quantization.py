import numpy as np
import pytest

from kestrel_serving.quantization import quantize_asymmetric, quantize_symmetric, relative_error, topk_overlap


@pytest.fixture
def weights():
    return np.random.default_rng(0).normal(0, 0.02, size=(256, 512)).astype(np.float32)


@pytest.mark.parametrize("bits", [8, 4])
def test_symmetric_error_is_at_most_half_a_step(weights, bits):
    q = quantize_symmetric(weights, bits=bits, per_channel=True)
    err = np.abs(weights - q.dequantize())
    assert np.all(err <= q.scale / 2 + 1e-7)


@pytest.mark.parametrize("bits", [8, 4])
def test_asymmetric_error_is_at_most_half_a_step(weights, bits):
    q = quantize_asymmetric(weights, bits=bits, per_channel=True)
    assert np.all(np.abs(weights - q.dequantize()) <= q.scale / 2 + 1e-6)


def test_fewer_bits_smaller_but_less_accurate(weights):
    q8, q4 = quantize_symmetric(weights, 8), quantize_symmetric(weights, 4)
    assert q4.nbytes() < q8.nbytes() < weights.nbytes
    assert q8.nbytes() == pytest.approx(weights.nbytes / 4, rel=0.02)
    assert relative_error(weights, q8.dequantize()) < 0.01 < relative_error(weights, q4.dequantize())


def test_per_channel_beats_per_tensor_with_outliers(weights):
    w = weights.copy()
    w[0, 0] = 2.0  # one outlier
    per_tensor = relative_error(w, quantize_symmetric(w, 4, per_channel=False).dequantize())
    per_channel = relative_error(w, quantize_symmetric(w, 4, per_channel=True).dequantize())
    assert per_channel < per_tensor


def test_int8_embeddings_keep_neighbours():
    rng = np.random.default_rng(1)
    corpus = rng.normal(size=(1000, 64)).astype(np.float32)
    queries = rng.normal(size=(50, 64)).astype(np.float32)
    q8 = quantize_symmetric(corpus, 8).dequantize()
    assert topk_overlap(queries, corpus, q8, k=10) >= 0.9
