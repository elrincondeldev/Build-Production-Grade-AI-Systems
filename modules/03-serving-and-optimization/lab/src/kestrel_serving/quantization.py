"""Post-training quantization from first principles, in NumPy. 📖 Lesson 3.6.

Real toolkits (bitsandbytes, GPTQ, AWQ, llama.cpp's GGUF formats) are cleverer, but
they all start from these two mappings:

symmetric:   q = round(w / scale),                scale = max|w| / qmax
asymmetric:  q = round(w / scale) + zero_point,   scale = (max - min) / (qmax - qmin)
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class Quantized:
    q: np.ndarray  # integer codes (stored in int8/uint8 containers even for 4-bit)
    scale: np.ndarray
    zero_point: np.ndarray
    bits: int

    def dequantize(self) -> np.ndarray:
        return (self.q.astype(np.float32) - self.zero_point) * self.scale

    def nbytes(self) -> int:
        """Storage if codes were packed tightly (4-bit = two codes per byte) + fp32 scales/zero points."""
        codes = self.q.size * self.bits / 8
        metadata = (self.scale.size + self.zero_point.size) * 4
        return int(codes + metadata)


def _reduce_axes(w: np.ndarray, per_channel: bool) -> tuple[int, ...] | None:
    # per-channel = one scale per output row; per-tensor = one scale for everything
    return tuple(range(1, w.ndim)) if per_channel else None


def quantize_symmetric(w: np.ndarray, bits: int = 8, per_channel: bool = True) -> Quantized:
    qmax = 2 ** (bits - 1) - 1  # 127 for int8, 7 for int4 (we drop -128/-8 to keep it symmetric)
    max_abs = np.max(np.abs(w), axis=_reduce_axes(w, per_channel), keepdims=True)
    scale = np.maximum(max_abs, 1e-12) / qmax
    q = np.clip(np.round(w / scale), -qmax, qmax).astype(np.int8)
    return Quantized(q, scale.astype(np.float32), np.zeros_like(scale, dtype=np.float32), bits)


def quantize_asymmetric(w: np.ndarray, bits: int = 8, per_channel: bool = True) -> Quantized:
    qmin, qmax = 0, 2**bits - 1  # 0..255 for uint8, 0..15 for uint4
    axes = _reduce_axes(w, per_channel)
    w_min = np.min(w, axis=axes, keepdims=True)
    w_max = np.max(w, axis=axes, keepdims=True)
    scale = np.maximum(w_max - w_min, 1e-12) / (qmax - qmin)
    zero_point = np.round(qmin - w_min / scale)
    q = np.clip(np.round(w / scale) + zero_point, qmin, qmax).astype(np.uint8)
    return Quantized(q, scale.astype(np.float32), zero_point.astype(np.float32), bits)


def relative_error(original: np.ndarray, approx: np.ndarray) -> float:
    """||W - W_hat|| / ||W||  (Frobenius norm)."""
    return float(np.linalg.norm(original - approx) / np.linalg.norm(original))


def topk_overlap(queries: np.ndarray, corpus: np.ndarray, corpus_approx: np.ndarray, k: int = 10) -> float:
    """Average fraction of the true top-k neighbours still found after quantization (recall@k)."""
    def normalise(m: np.ndarray) -> np.ndarray:
        return m / np.linalg.norm(m, axis=1, keepdims=True)

    true_top = np.argsort(-(normalise(queries) @ normalise(corpus).T), axis=1)[:, :k]
    approx_top = np.argsort(-(normalise(queries) @ normalise(corpus_approx).T), axis=1)[:, :k]
    overlaps = [len(set(a) & set(b)) / k for a, b in zip(true_top, approx_top)]
    return float(np.mean(overlaps))
