"""Index building and hybrid retrieval. 📖 Lesson 2.5.

    query ─┬─► BM25 (keywords) ──► top-N ─┐
           │                              ├─► RRF fusion ─► rerank ─► top-k chunks
           └─► embed ─► vector search ────┘
    (both retrievers apply the same access filter: a chunk the user may not read
     must never enter the candidate list, not even to be filtered out later)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from kestrel_docs.adapters.embeddings import Embedder
from kestrel_docs.adapters.vector_store import QdrantStore
from kestrel_docs.domain.chunking import Chunk, chunk_document
from kestrel_docs.domain.documents import Document
from kestrel_docs.domain.fusion import reciprocal_rank_fusion
from kestrel_docs.domain.lexical import BM25Index
from kestrel_docs.domain.rerank import Reranker
from kestrel_docs.domain.roles import allowed_access

Mode = Literal["bm25", "dense", "hybrid"]


@dataclass
class RetrievedChunk:
    chunk: Chunk
    score: float
    debug: dict = field(default_factory=dict)  # per-retriever ranks, handy when debugging relevance


class HandbookIndex:
    """Everything needed to search the corpus: chunks, BM25 index and vector store."""

    def __init__(self, docs: list[Document], embedder: Embedder, chunk_size: int = 600, chunk_overlap: int = 100):
        self.docs = {d.doc_id: d for d in docs}
        self.embedder = embedder
        self.chunks: list[Chunk] = [c for d in docs for c in chunk_document(d, chunk_size, chunk_overlap)]
        self.by_id = {c.chunk_id: c for c in self.chunks}
        self.store = QdrantStore(dim=embedder.dim)
        self.store.upsert(self.chunks, embedder.embed([c.embed_text for c in self.chunks]))
        self.bm25 = BM25Index(self.chunks)


class Retriever:
    def __init__(self, index: HandbookIndex, reranker: Reranker | None = None, candidates: int = 20):
        self.index = index
        self.reranker = reranker
        self.candidates = candidates

    def retrieve(self, query: str, role: str, *, mode: Mode = "hybrid", top_k: int = 4, rerank: bool = True) -> list[RetrievedChunk]:
        access = allowed_access(role)
        n = self.candidates
        bm = self.index.bm25.search(query, n, access) if mode in ("bm25", "hybrid") else []
        dense = (
            [(h.chunk_id, h.score) for h in self.index.store.search(self.index.embedder.embed([query])[0], n, access)]
            if mode in ("dense", "hybrid") else []
        )
        if mode == "bm25":
            ranked = bm
        elif mode == "dense":
            ranked = dense
        else:
            ranked = reciprocal_rank_fusion([[cid for cid, _ in bm], [cid for cid, _ in dense]])

        bm_rank = {cid: r for r, (cid, _) in enumerate(bm, 1)}
        dense_rank = {cid: r for r, (cid, _) in enumerate(dense, 1)}
        results = [
            RetrievedChunk(self.index.by_id[cid], score, {"bm25_rank": bm_rank.get(cid), "dense_rank": dense_rank.get(cid)})
            for cid, score in ranked[:n]
        ]
        if rerank and self.reranker is not None and results:
            reranked = self.reranker.rerank(query, [r.chunk for r in results])
            debug = {r.chunk.chunk_id: r.debug for r in results}
            results = [RetrievedChunk(c, s, debug[c.chunk_id]) for c, s in reranked]
        return results[:top_k]
