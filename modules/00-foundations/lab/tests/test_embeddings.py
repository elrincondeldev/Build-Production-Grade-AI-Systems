import math

import pytest

from kestrel_foundations.embeddings import (
    cosine,
    handbook_sentences,
    hash_embed,
    rank,
    strip_front_matter,
    tokenize,
)
from kestrel_foundations.paths import handbook_dir


def test_hash_embed_is_unit_length_and_deterministic():
    v = hash_embed("freeze my card")
    assert len(v) == 1024
    assert math.isclose(sum(x * x for x in v), 1.0, rel_tol=1e-9)
    assert v == hash_embed("freeze my card")


def test_cosine_basics():
    assert cosine([1, 0], [1, 0]) == pytest.approx(1.0)
    assert cosine([1, 0], [0, 1]) == pytest.approx(0.0)
    assert cosine([1, 0], [-1, 0]) == pytest.approx(-1.0)
    with pytest.raises(ValueError):
        cosine([1, 0], [1, 0, 0])


def test_shared_words_score_higher_than_unrelated():
    card = hash_embed("freeze my card")
    assert cosine(card, hash_embed("block my card")) > cosine(card, hash_embed("vacation days per year"))


def test_tokenize_drops_stopwords():
    assert tokenize("How do I freeze my card?") == ["freeze", "card"]


def test_strip_front_matter():
    assert strip_front_matter("---\na: 1\n---\n# Title").strip() == "# Title"


def test_handbook_sentences_skip_hidden_comments():
    sentences = handbook_sentences(handbook_dir())
    assert len(sentences) > 50
    assert not any("Ignore all previous instructions" in s for _, s in sentences)


def test_rank_finds_refund_policy():
    sentences = handbook_sentences(handbook_dir())
    top = rank("refund fee within 60 days", sentences, top_k=3)
    assert top[0][1] == "refund-policy"
    assert top[0][0] >= top[-1][0]
