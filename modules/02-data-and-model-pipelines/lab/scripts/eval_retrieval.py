"""Compare retrieval strategies on the golden set.

    uv run python scripts/eval_retrieval.py
    KESTREL_EMBEDDINGS_PROVIDER=sentence-transformers uv run python scripts/eval_retrieval.py   # needs --extra semantic
"""

from __future__ import annotations

from kestrel_docs.config import get_settings
from kestrel_docs.evaluation import evaluate, load_golden
from kestrel_docs.service import build_services

CONFIGS = [("bm25", False), ("dense", False), ("hybrid", False), ("hybrid", True)]


def main() -> None:
    settings = get_settings()
    svc = build_services(settings)
    golden = load_golden(settings.resolved_golden_path())
    print(f"embeddings={settings.embeddings_provider}  reranker={settings.reranker}  "
          f"chunks={len(svc.index.chunks)}  questions={len(golden)}\n")
    print("| retriever | recall@1 | recall@3 | recall@5 | MRR |")
    print("|---|---|---|---|---|")
    for mode, rerank in CONFIGS:
        s = evaluate(svc.retriever, golden, mode=mode, rerank=rerank)
        print(f"| {s.name} | {s.recall[1]:.2f} | {s.recall[3]:.2f} | {s.recall[5]:.2f} | {s.mrr:.2f} |")


if __name__ == "__main__":
    main()
