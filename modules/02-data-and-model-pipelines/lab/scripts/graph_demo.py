"""A toy GraphRAG index: entities + co-occurrence edges + 'communities'. 📖 Lesson 2.5.

Real GraphRAG (e.g. Microsoft's) asks an LLM to extract entities and relations
from every chunk, clusters the graph into communities and writes a summary per
community. That lets it answer *global* questions ("what are the main themes
across all policies?") that top-k chunk retrieval cannot.

Here we fake the LLM extraction with a fixed entity dictionary so the whole
idea fits on one screen and runs offline:

    uv run python scripts/graph_demo.py
    uv run python scripts/graph_demo.py --entity "director"
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from itertools import combinations

from kestrel_docs.config import get_settings
from kestrel_docs.domain.chunking import chunk_document
from kestrel_docs.domain.documents import load_corpus

# In real GraphRAG an LLM extracts these. A dictionary keeps the demo deterministic.
ENTITIES = [
    "director", "manager", "support", "people team", "finance", "sre", "incident commander",
    "sev1", "sev2", "canary", "rollback", "postmortem", "on-call", "page",
    "refund", "dispute", "fraud", "card", "fx", "atm", "premium", "plus", "basic",
    "expenses", "vacation", "parental leave", "salary", "promotion", "budget", "llm api", "gpu",
]


def extract(text: str) -> set[str]:
    t = text.lower()
    return {e for e in ENTITIES if e in t}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--entity", default="director")
    args = parser.parse_args()

    docs = load_corpus(get_settings().resolved_handbook_dir())
    edges: Counter[tuple[str, str]] = Counter()
    mentions: dict[str, set[str]] = defaultdict(set)
    for d in docs:
        for c in chunk_document(d):
            ents = extract(c.embed_text)
            for e in ents:
                mentions[e].add(d.doc_id)
            for a, b in combinations(sorted(ents), 2):
                edges[(a, b)] += 1

    neighbours: dict[str, Counter[str]] = defaultdict(Counter)
    for (a, b), w in edges.items():
        neighbours[a][b] += w
        neighbours[b][a] += w

    print(f"graph: {len(mentions)} entities, {len(edges)} edges\n")
    e = args.entity.lower()
    print(f"'{e}' appears in: {sorted(mentions.get(e, []))}")
    print(f"'{e}' is connected to: {neighbours[e].most_common(8)}\n")

    # Communities = connected components over edges seen at least twice (a crude stand-in for Leiden).
    strong = defaultdict(set)
    for (a, b), w in edges.items():
        if w >= 2:
            strong[a].add(b)
            strong[b].add(a)
    seen, communities = set(), []
    for node in strong:
        if node in seen:
            continue
        stack, comp = [node], set()
        while stack:
            n = stack.pop()
            if n not in comp:
                comp.add(n)
                stack.extend(strong[n] - comp)
        seen |= comp
        communities.append(sorted(comp))
    for i, comp in enumerate(sorted(communities, key=len, reverse=True), 1):
        docs_in = sorted({doc for ent in comp for doc in mentions[ent]})
        print(f"community {i}: {comp}\n   docs: {docs_in}")
    print("\nIn real GraphRAG an LLM would now write a summary per community, and global questions are answered from those summaries.")


if __name__ == "__main__":
    main()
