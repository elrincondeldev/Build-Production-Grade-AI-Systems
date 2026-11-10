"""Embedding providers.

``HashEmbedder`` is a *feature-hashing* bag of words + bigrams. It needs no download
and is fully deterministic, which makes it perfect for tests and CI. It only captures
word overlap, not meaning, so it will miss paraphrases a real model would catch.
Install the ``st`` extra to use a real sentence-transformers model.
"""

from __future__ import annotations

import hashlib
import re
from typing import Protocol

import numpy as np

_WORD = re.compile(r"[a-z0-9€%]+")
_STOP = {"a", "an", "the", "is", "are", "do", "does", "i", "my", "to", "of", "for", "in", "on", "can", "what", "how"}


class Embedder(Protocol):
    dim: int

    def embed(self, texts: list[str]) -> np.ndarray: ...


class HashEmbedder:
    def __init__(self, dim: int = 512) -> None:
        self.dim = dim

    def _bucket(self, feature: str) -> tuple[int, float]:
        # ⚠️ Never use Python's built-in hash() here: it is salted per process,
        # so vectors would change between restarts and between replicas.
        digest = hashlib.md5(feature.encode()).digest()
        index = int.from_bytes(digest[:4], "little") % self.dim
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        return index, sign

    def embed(self, texts: list[str]) -> np.ndarray:
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for row, text in enumerate(texts):
            words = [w for w in _WORD.findall(text.lower()) if w not in _STOP]
            features = words + [f"{a}_{b}" for a, b in zip(words, words[1:])]
            for feature in features:
                index, sign = self._bucket(feature)
                out[row, index] += sign
        norms = np.linalg.norm(out, axis=1, keepdims=True)
        return out / np.maximum(norms, 1e-12)


class SentenceTransformerEmbedder:  # pragma: no cover - optional heavy dependency
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)
        self.dim = self._model.get_sentence_embedding_dimension()

    def embed(self, texts: list[str]) -> np.ndarray:
        return np.asarray(self._model.encode(texts, normalize_embeddings=True), dtype=np.float32)


def build_embedder(provider: str) -> Embedder:
    if provider == "sentence-transformers":
        return SentenceTransformerEmbedder()
    return HashEmbedder()
