import numpy as np
import pytest

from kestrel_docs.adapters.embeddings import HashEmbedder
from kestrel_docs.adapters.vector_store import QdrantStore
from kestrel_docs.domain.chunking import Chunk
from kestrel_docs.domain.context import pack_context
from kestrel_docs.domain.fusion import reciprocal_rank_fusion
from kestrel_docs.evaluation import evaluate, load_golden


def _chunks():
    return [
        Chunk("a#000", "a", "A", "public", "", "refund within 60 days", 0),
        Chunk("b#000", "b", "B", "hr", "", "salary band senior engineer", 0),
    ]


def test_rrf_math():
    fused = dict(reciprocal_rank_fusion([["x", "y"], ["y", "z"]], k=60))
    assert fused["y"] == pytest.approx(1 / 62 + 1 / 61)  # 2nd in list 1, 1st in list 2
    assert fused["x"] == pytest.approx(1 / 61)
    assert fused["z"] == pytest.approx(1 / 62)
    assert max(fused, key=fused.get) == "y"  # agreement beats a single first place


def test_upsert_is_idempotent():
    emb = HashEmbedder()
    store = QdrantStore(dim=emb.dim, collection="t1")
    chunks = _chunks()
    vecs = emb.embed([c.text for c in chunks])
    store.upsert(chunks, vecs)
    store.upsert(chunks, vecs)  # re-ingest the same content
    assert store.count() == 2


def test_metadata_filter_hides_forbidden_chunks():
    emb = HashEmbedder()
    store = QdrantStore(dim=emb.dim, collection="t2")
    chunks = _chunks()
    store.upsert(chunks, emb.embed([c.text for c in chunks]))
    q = emb.embed(["salary band senior engineer"])[0]
    assert store.search(q, k=5)[0].chunk_id == "b#000"
    assert {h.chunk_id for h in store.search(q, k=5, allowed_access=["public"])} == {"a#000"}


def test_hash_embeddings_are_deterministic_and_normalised():
    e = HashEmbedder()
    a, b = e.embed(["refund policy"]), e.embed(["refund policy"])
    assert np.array_equal(a, b)
    assert np.linalg.norm(a[0]) == pytest.approx(1.0, abs=1e-5)


def test_role_filter_applies_to_both_retrievers(services):
    for mode in ("bm25", "dense", "hybrid"):
        hits = services.retriever.retrieve("salary band Staff Engineer", "customer", mode=mode, top_k=10)
        assert all(h.chunk.access == "public" for h in hits), mode


def test_context_respects_budget_and_sandwich_order(services):
    hits = services.retriever.retrieve("refund fee days", "customer", top_k=6)
    pack = pack_context(hits, token_budget=200)
    assert pack.tokens <= 200
    assert pack.used[0].chunk.chunk_id == hits[0].chunk.chunk_id
    full = pack_context(hits, token_budget=10_000, order="sandwich")
    if len(full.used) > 2:
        assert full.used[-1].chunk.chunk_id == hits[1].chunk.chunk_id


def test_retrieval_eval_runs_and_hybrid_is_strong(services, settings):
    golden = load_golden(settings.resolved_golden_path())
    assert len(golden) == 27
    hybrid = evaluate(services.retriever, golden, mode="hybrid", rerank=False)
    assert hybrid.recall[5] >= 0.9
    assert 0 < hybrid.mrr <= 1
