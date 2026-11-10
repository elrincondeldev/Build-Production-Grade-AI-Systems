"""See what quantization does to weights and to embeddings. 📖 Lesson 3.6.

    uv run python scripts/quantize_demo.py
"""

from __future__ import annotations

import numpy as np

from kestrel_serving.quantization import quantize_asymmetric, quantize_symmetric, relative_error, topk_overlap


def weights_demo(rng: np.random.Generator) -> None:
    # A transformer-like weight matrix: mostly small Gaussian values plus a few large
    # outliers (real LLM weights and especially activations have them).
    w = rng.normal(0, 0.02, size=(1024, 4096)).astype(np.float32)
    outliers = rng.choice(w.size, size=200, replace=False)
    w.flat[outliers] = rng.normal(0, 0.5, size=200)
    fp32_mb = w.nbytes / 1e6

    print("## Weight matrix 1024 x 4096 (4.2M parameters)\n")
    print(f"| format | size (MB) | vs fp32 | relative error |\n|---|---|---|---|")
    print(f"| fp32 | {fp32_mb:.1f} | 1.00x | 0 |")
    print(f"| fp16 | {fp32_mb / 2:.1f} | 0.50x | {relative_error(w, w.astype(np.float16).astype(np.float32)):.5f} |")
    for name, fn, bits, per_channel in [
        ("int8 symmetric, per-tensor", quantize_symmetric, 8, False),
        ("int8 symmetric, per-channel", quantize_symmetric, 8, True),
        ("int4 symmetric, per-tensor", quantize_symmetric, 4, False),
        ("int4 symmetric, per-channel", quantize_symmetric, 4, True),
        ("int4 asymmetric, per-channel", quantize_asymmetric, 4, True),
    ]:
        q = fn(w, bits=bits, per_channel=per_channel)
        mb = q.nbytes() / 1e6
        print(f"| {name} | {mb:.1f} | {mb / fp32_mb:.2f}x | {relative_error(w, q.dequantize()):.5f} |")
    print("\nNotice: one outlier stretches a per-tensor scale for *every* weight; per-channel scales contain the damage.\n")


def embeddings_demo(rng: np.random.Generator) -> None:
    # 5,000 document embeddings with some cluster structure, 384-d like all-MiniLM-L6-v2.
    centers = rng.normal(size=(50, 384))
    corpus = (centers[rng.integers(0, 50, 5000)] + rng.normal(scale=0.8, size=(5000, 384))).astype(np.float32)
    queries = (centers[rng.integers(0, 50, 200)] + rng.normal(scale=0.8, size=(200, 384))).astype(np.float32)

    print("## Embedding index: 5,000 x 384 vectors, 200 queries\n")
    print("| format | index size (MB) | recall@10 vs fp32 |\n|---|---|---|")
    print(f"| fp32 | {corpus.nbytes / 1e6:.2f} | 1.000 |")
    for bits in (8, 4):
        q = quantize_symmetric(corpus, bits=bits, per_channel=True)
        print(f"| int{bits} | {q.nbytes() / 1e6:.2f} | {topk_overlap(queries, corpus, q.dequantize()):.3f} |")
    binary = np.where(corpus > 0, 1.0, -1.0).astype(np.float32)
    print(f"| 1-bit (sign) | {corpus.size / 8 / 1e6:.2f} | {topk_overlap(queries, corpus, binary):.3f} |")
    print("\nVector DBs use exactly this trade-off: quantized search first, then re-score the shortlist in full precision.")


if __name__ == "__main__":
    generator = np.random.default_rng(0)
    weights_demo(generator)
    embeddings_demo(generator)
