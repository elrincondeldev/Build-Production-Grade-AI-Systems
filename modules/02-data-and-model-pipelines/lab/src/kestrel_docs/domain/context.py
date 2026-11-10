"""Context packaging: which chunks go into the prompt, in what order, under what budget. 📖 Lesson 2.5.

Three rules:
1. **Budget**: stop adding chunks before the token cap (cost and latency grow with
   every token; quality often *drops* with too much context).
2. **Order**: LLMs attend best to the start and end of a long context ("lost in
   the middle"). `sandwich` puts the best chunk first and the second-best last.
3. **Cite**: every block is labelled `[doc_id]`, so the model can cite and we can
   verify that each citation points to a source we actually provided.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from kestrel_docs.adapters.llm import approx_tokens
from kestrel_docs.domain.retrieval import RetrievedChunk


@dataclass
class ContextPack:
    text: str
    used: list[RetrievedChunk]
    dropped: list[RetrievedChunk]
    tokens: int

    @property
    def doc_ids(self) -> set[str]:
        return {r.chunk.doc_id for r in self.used}


def format_block(r: RetrievedChunk) -> str:
    return f"[{r.chunk.doc_id}] {r.chunk.header}\n{r.chunk.text}\n"


def pack_context(
    retrieved: list[RetrievedChunk],
    token_budget: int = 900,
    order: Literal["relevance", "sandwich"] = "sandwich",
) -> ContextPack:
    used, dropped, seen, tokens = [], [], set(), 0
    for r in retrieved:  # `retrieved` is already sorted best-first
        if r.chunk.chunk_id in seen:
            continue
        cost = approx_tokens(format_block(r))
        if tokens + cost > token_budget:
            dropped.append(r)
            continue
        used.append(r)
        seen.add(r.chunk.chunk_id)
        tokens += cost
    if order == "sandwich" and len(used) > 2:
        used = [used[0], *used[2:], used[1]]
    return ContextPack("\n".join(format_block(r) for r in used), used, dropped, tokens)
