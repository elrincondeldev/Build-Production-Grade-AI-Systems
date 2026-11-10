import pytest

from kestrel_serving.adapters.cache import ExactCache, SemanticCache, normalize
from kestrel_serving.adapters.embeddings import HashEmbedder


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def test_normalize_ignores_case_whitespace_punctuation():
    assert normalize("  How many  days?? ") == normalize("how many days")


def test_exact_cache_hit_miss_and_scope():
    cache = ExactCache()
    assert cache.get("What is the FX markup?") is None
    cache.put("What is the FX markup?", "0.5%", scope="v1")
    assert cache.get("what is the fx markup", scope="v1") == "0.5%"
    assert cache.get("What is the FX markup?", scope="v2") is None  # new prompt version = new key
    assert cache.stats.hits == 1 and cache.stats.misses == 2


def test_exact_cache_ttl_and_lru_eviction():
    clock = FakeClock()
    cache = ExactCache(ttl_s=10, max_entries=2, clock=clock)
    cache.put("a question", 1)
    clock.now = 11
    assert cache.get("a question") is None  # expired
    cache.put("q1", 1)
    cache.put("q2", 2)
    cache.get("q1")  # q1 is now most recently used
    cache.put("q3", 3)  # evicts q2
    assert cache.get("q2") is None and cache.get("q1") == 1


def test_semantic_cache_paraphrase_hit():
    cache = SemanticCache(HashEmbedder(), threshold=0.8)
    cache.put("How long do I have to open a card dispute?", "120 days")
    hit = cache.get("how long do i have to open a card dispute")
    assert hit is not None and hit.value == "120 days" and hit.similarity > 0.99


def test_semantic_cache_threshold_controls_false_hits():
    embedder = HashEmbedder()
    q_cached = "How many days do I have to request a refund for a fee?"
    q_other = "How many days do I have to open a card dispute?"  # different question, similar words
    sim = float(embedder.embed([normalize(q_cached)])[0] @ embedder.embed([normalize(q_other)])[0])
    assert 0.2 < sim < 0.9

    loose = SemanticCache(embedder, threshold=sim - 0.01)
    loose.put(q_cached, "60 days")
    assert loose.get(q_other).value == "60 days"  # ❌ false hit: wrong answer served

    strict = SemanticCache(embedder, threshold=sim + 0.01)
    strict.put(q_cached, "60 days")
    assert strict.get(q_other) is None


def test_semantic_cache_respects_scope_and_ttl():
    clock = FakeClock()
    cache = SemanticCache(HashEmbedder(), threshold=0.9, ttl_s=5, clock=clock)
    cache.put("What is the learning budget?", "€1,200", scope="employee")
    assert cache.get("What is the learning budget?", scope="customer") is None
    assert cache.get("What is the learning budget?", scope="employee") is not None
    clock.now = 6
    assert cache.get("What is the learning budget?", scope="employee") is None
    assert len(cache) == 0


@pytest.mark.parametrize("threshold", [0.0, 0.5, 1.0])
def test_semantic_cache_empty_is_miss(threshold):
    cache = SemanticCache(HashEmbedder(), threshold=threshold)
    assert cache.get("anything") is None
    assert cache.stats.misses == 1
