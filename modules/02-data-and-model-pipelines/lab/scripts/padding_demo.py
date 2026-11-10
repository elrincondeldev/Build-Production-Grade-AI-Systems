"""How much compute do we waste on padding? 📖 Lesson 2.3.

Sequences in a batch must have the same length, so short ones are padded.
Padding tokens cost compute but carry no information. This script compares
three batching strategies on 10,000 sequences with realistic, skewed lengths:

    uv run python scripts/padding_demo.py
"""

from __future__ import annotations

import numpy as np

rng = np.random.default_rng(0)
lengths = np.clip(rng.lognormal(mean=4.5, sigma=0.7, size=10_000).astype(int), 8, 2048)  # tokens per sequence
BATCH = 32
MAX_LEN = 512


def waste(batches: list[np.ndarray], pad_to: int | None = None) -> tuple[float, int]:
    real = padded = 0
    for b in batches:
        b = np.minimum(b, MAX_LEN)  # truncate long sequences
        width = pad_to or int(b.max())
        real += int(b.sum())
        padded += width * len(b)
    return 1 - real / padded, padded


def batches_of(order: np.ndarray) -> list[np.ndarray]:
    return [lengths[order[i:i + BATCH]] for i in range(0, len(order), BATCH)]


random_order = rng.permutation(len(lengths))
strategies = {
    "static padding to 512": waste(batches_of(random_order), pad_to=MAX_LEN),
    "dynamic padding (pad to longest in batch)": waste(batches_of(random_order)),
}
# Bucketing: sort by length inside large random windows, then batch, then shuffle the batches.
window = BATCH * 50
bucketed = np.concatenate([
    random_order[i:i + window][np.argsort(lengths[random_order[i:i + window]])]
    for i in range(0, len(random_order), window)
])
b = batches_of(bucketed)
rng.shuffle(b)
strategies["length bucketing + dynamic padding"] = waste(b)

print(f"{len(lengths):,} sequences, median length {int(np.median(lengths))} tokens, "
      f"p95 {int(np.percentile(lengths, 95))}, batch size {BATCH}, max length {MAX_LEN}\n")
base = strategies["static padding to 512"][1]
for name, (w, tokens) in strategies.items():
    print(f"{name:<45} padding waste {w:6.1%}   tokens processed {tokens:>10,}  ({tokens / base:.0%} of static)")
