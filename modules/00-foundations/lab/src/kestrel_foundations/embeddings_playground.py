"""CLI: search the handbook with embeddings.

    uv run embeddings-playground
    uv run embeddings-playground --query "Can I get my money back for a fee?"
    uv sync --extra semantic && uv run embeddings-playground --semantic   # real model (~90 MB download)
"""

from __future__ import annotations

import argparse

from .embeddings import cosine, handbook_sentences, hash_embed, rank
from .paths import handbook_dir

PAIRS = [
    ("freeze my card", "block my card"),
    ("freeze my card", "how many vacation days do I get"),
    ("refund a fee", "get my money back for a charge"),
]


def _semantic_embedder():
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:  # pragma: no cover - optional extra
        raise SystemExit("Install the optional extra first: uv sync --extra semantic") from exc
    model = SentenceTransformer("all-MiniLM-L6-v2")
    return lambda text: model.encode(text, normalize_embeddings=True).tolist()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Embeddings playground (Lab 0).")
    parser.add_argument("--query", default="I don't recognise a payment on my card")
    parser.add_argument("--semantic", action="store_true", help="use sentence-transformers instead of hash embeddings")
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args(argv)

    embed = _semantic_embedder() if args.semantic else hash_embed
    label = "all-MiniLM-L6-v2" if args.semantic else "hash embeddings (1024 dims)"
    print(f"Embedder: {label}\n")

    print("Pairwise similarity:")
    for a, b in PAIRS:
        print(f"  {cosine(embed(a), embed(b)):+.3f}  '{a}'  vs  '{b}'")

    sentences = handbook_sentences(handbook_dir())
    print(f"\nSearching {len(sentences)} handbook sentences for: '{args.query}'")
    for score, doc, sentence in rank(args.query, sentences, embed=embed, top_k=args.top_k):
        short = sentence if len(sentence) <= 100 else sentence[:97] + "..."
        print(f"  {score:+.3f}  [{doc}] {short}")


if __name__ == "__main__":
    main()
