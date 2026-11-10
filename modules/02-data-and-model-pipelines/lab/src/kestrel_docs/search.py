"""Ask the retriever directly, without the LLM, to debug relevance.

    uv run python -m kestrel_docs.search "Can I deploy on Friday?" --role engineer --mode hybrid
"""

from __future__ import annotations

import argparse

from kestrel_docs.config import get_settings
from kestrel_docs.service import build_services


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("question")
    parser.add_argument("--role", default="customer")
    parser.add_argument("--mode", default="hybrid", choices=["bm25", "dense", "hybrid"])
    parser.add_argument("--no-rerank", action="store_true")
    parser.add_argument("-k", type=int, default=5)
    args = parser.parse_args()
    svc = build_services(get_settings())
    hits = svc.retriever.retrieve(args.question, args.role, mode=args.mode, top_k=args.k, rerank=not args.no_rerank)
    if not hits:
        print("(no results for this role)")
    for i, h in enumerate(hits, 1):
        preview = h.chunk.text.replace("\n", " ")[:90]
        print(f"{i}. {h.chunk.chunk_id:<32} score={h.score:.4f} bm25#={h.debug.get('bm25_rank')} dense#={h.debug.get('dense_rank')}")
        print(f"   {h.chunk.header} | {preview}…")


if __name__ == "__main__":
    main()
