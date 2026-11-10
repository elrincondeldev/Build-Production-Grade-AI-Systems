"""Back-of-the-envelope memory and parameter maths for fine-tuning. 📖 Lesson 2.7.

    uv run python scripts/lora_math.py
    uv run python scripts/lora_math.py --hidden 2048 --layers 16 --mlp 8192 --rank 16

Rules of thumb used (mixed-precision training with the Adam optimizer, activations excluded):
  full fine-tuning  ≈ 16 bytes per parameter
                      (2 bf16 weights + 2 bf16 grads + 4 fp32 master weights + 8 fp32 Adam moments)
  LoRA              ≈ 2 bytes per frozen parameter (bf16) + 16 bytes per *trainable* adapter parameter
  QLoRA             ≈ 0.5 bytes per frozen parameter (4-bit) + 16 bytes per adapter parameter
Real numbers vary with framework, sequence length and batch size (activations can dominate).
"""

from __future__ import annotations

import argparse


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    # Defaults resemble a typical ~8B-parameter decoder-only model (grouped-query attention).
    p.add_argument("--hidden", type=int, default=4096)
    p.add_argument("--layers", type=int, default=32)
    p.add_argument("--mlp", type=int, default=14336)
    p.add_argument("--kv-dim", type=int, default=1024, help="key/value projection width (grouped-query attention)")
    p.add_argument("--vocab", type=int, default=128_256)
    p.add_argument("--rank", type=int, default=8)
    a = p.parse_args()

    h, L = a.hidden, a.layers
    attn = h * h * 2 + h * a.kv_dim * 2            # q, o (h×h) and k, v (h×kv)
    mlp = 3 * h * a.mlp                             # gate, up, down projections
    total = L * (attn + mlp) + 2 * a.vocab * h      # + input embeddings and output head

    # LoRA on all attention + MLP projections: each W (d_out×d_in) gets B (d_out×r) and A (r×d_in)
    shapes = [(h, h), (a.kv_dim, h), (a.kv_dim, h), (h, h), (a.mlp, h), (a.mlp, h), (h, a.mlp)]
    lora = L * sum(a.rank * (d_out + d_in) for d_out, d_in in shapes)

    gb = 1e9
    print(f"model parameters        ≈ {total / 1e9:5.2f} B")
    print(f"LoRA rank {a.rank:<3} adapters  ≈ {lora / 1e6:5.1f} M trainable ({lora / total:.2%} of the model)\n")
    print(f"{'method':<18}{'weights':>10}{'training state':>16}{'≈ total (no activations)':>28}")
    rows = [
        ("full fine-tune", total * 2, total * 14),
        ("LoRA (bf16 base)", total * 2, lora * 16),
        ("QLoRA (4-bit base)", total * 0.5, lora * 16),
    ]
    for name, weights, state in rows:
        print(f"{name:<18}{weights / gb:>8.1f} GB{state / gb:>14.1f} GB{(weights + state) / gb:>24.1f} GB")
    print(f"\nadapter file on disk (bf16) ≈ {lora * 2 / 1e6:.0f} MB, vs ≈ {total * 2 / gb:.0f} GB for a full copy of the model")


if __name__ == "__main__":
    main()
