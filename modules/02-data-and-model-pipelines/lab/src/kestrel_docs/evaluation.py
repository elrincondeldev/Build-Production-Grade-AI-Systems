"""Retrieval evaluation on the golden set: recall@k and MRR at document level. 📖 Lesson 2.5.

- recall@k: share of questions where at least one expected document appears in the top k.
- MRR (mean reciprocal rank): average of 1/rank of the first correct document (0 if none in the list).
  MRR rewards putting the right document *first*, which matters because the
  generator reads the first chunks most carefully.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from kestrel_docs.domain.retrieval import Mode, Retriever


@dataclass
class RetrievalScores:
    name: str
    n: int
    recall: dict[int, float]
    mrr: float


def load_golden(path: Path) -> list[dict]:
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    # Questions without an expected document (refusals, unanswerable) test generation, not retrieval.
    return [r for r in rows if r["expected_doc_ids"]]


def ranked_doc_ids(retriever: Retriever, question: str, role: str, mode: Mode, rerank: bool, depth: int) -> list[str]:
    hits = retriever.retrieve(question, role, mode=mode, top_k=depth, rerank=rerank)
    return list(dict.fromkeys(h.chunk.doc_id for h in hits))


def evaluate(retriever: Retriever, golden: list[dict], *, mode: Mode, rerank: bool, ks: tuple[int, ...] = (1, 3, 5)) -> RetrievalScores:
    hits_at = {k: 0 for k in ks}
    rr_sum = 0.0
    for row in golden:
        docs = ranked_doc_ids(retriever, row["question"], row["role"], mode, rerank, depth=20)
        expected = set(row["expected_doc_ids"])
        first = next((i for i, d in enumerate(docs, 1) if d in expected), None)
        if first:
            rr_sum += 1 / first
        for k in ks:
            hits_at[k] += int(first is not None and first <= k)
    n = len(golden)
    name = f"{mode}{' + rerank' if rerank else ''}"
    return RetrievalScores(name, n, {k: hits_at[k] / n for k in ks}, rr_sum / n)
