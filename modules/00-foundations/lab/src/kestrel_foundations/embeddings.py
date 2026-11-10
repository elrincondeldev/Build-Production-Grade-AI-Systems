"""Embeddings and cosine similarity, from scratch.

📖 See lesson 0.5 "LLMs in one hour".

A *hash embedding* turns text into a fixed-size vector by hashing each word
(and word pair) into one of `dim` buckets. It is deterministic, instant and
needs no download, which is perfect for tests. But it only captures *shared
words*, not *meaning*: "freeze my card" and "block my card" overlap only on
"my card". Real embedding models (sentence-transformers, optional extra) learn
meaning from data. Comparing the two is the point of the playground.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Sequence
from pathlib import Path

_WORD = re.compile(r"[a-z0-9€%]+")
STOPWORDS = frozenset(
    "a an the and or of to in on for is are be can i my me you your it this that with at by from do does what how".split()
)


def tokenize(text: str) -> list[str]:
    return [w for w in _WORD.findall(text.lower()) if len(w) > 1 and w not in STOPWORDS]


def _bucket(feature: str, dim: int) -> tuple[int, float]:
    # hashlib, not Python's hash(): hash() is randomised per process, so vectors
    # would change between runs, which is a classic reproducibility bug.
    h = int.from_bytes(hashlib.blake2b(feature.encode(), digest_size=8).digest(), "big")
    return h % dim, (1.0 if (h >> 63) & 1 else -1.0)


def hash_embed(text: str, dim: int = 1024) -> list[float]:
    """Map text to a unit-length vector of `dim` floats."""
    vec = [0.0] * dim
    words = tokenize(text)
    features = words + [f"{a}_{b}" for a, b in zip(words, words[1:])]
    for f in features:
        i, sign = _bucket(f, dim)
        vec[i] += sign
    norm = math.sqrt(sum(v * v for v in vec))
    return [v / norm for v in vec] if norm else vec


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    """cos(θ) = (a·b) / (|a|·|b|). 1 = same direction, 0 = unrelated, -1 = opposite."""
    if len(a) != len(b):
        raise ValueError(f"dimension mismatch: {len(a)} vs {len(b)}")
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def strip_front_matter(markdown: str) -> str:
    if markdown.startswith("---"):
        end = markdown.find("\n---", 3)
        if end != -1:
            return markdown[end + 4 :]
    return markdown


def handbook_sentences(handbook: Path, min_words: int = 5) -> list[tuple[str, str]]:
    """Return (doc_id, sentence) pairs from the Markdown handbook files.

    Deliberately naive splitting: lesson 2.4 covers proper parsing and chunking.
    """
    out: list[tuple[str, str]] = []
    for path in sorted(handbook.glob("*.md")):
        if path.name == "README.md":
            continue
        text = strip_front_matter(path.read_text(encoding="utf-8"))
        text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)  # drop HTML comments
        text = re.sub(r"[*#`|>]", " ", text)
        for raw in re.split(r"(?<=[.!?])\s+|\n\s*\n|\n-\s|\n\d+\.\s", text):
            sentence = " ".join(raw.split()).lstrip("-• ").replace(" .", ".")
            if len(sentence.split()) >= min_words:
                out.append((path.stem, sentence))
    return out


def rank(query: str, sentences: list[tuple[str, str]], embed=hash_embed, top_k: int = 3) -> list[tuple[float, str, str]]:
    """Brute-force nearest neighbours: score every sentence, keep the best k.

    Fine for hundreds of sentences; lesson 2.5 shows vector indexes for millions.
    """
    q = embed(query)
    scored = [(cosine(q, embed(s)), doc, s) for doc, s in sentences]
    return sorted(scored, key=lambda t: t[0], reverse=True)[:top_k]
