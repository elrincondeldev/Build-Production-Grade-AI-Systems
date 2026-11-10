"""Embedding providers. 📖 Lesson 2.5.

`HashEmbedder` is a *feature-hashing* embedder: each word (and word pair) is
hashed into one of `dim` buckets. It understands no meaning ("refund" and
"money back" share nothing), but it is deterministic, instant and offline.
That makes it perfect for tests, and a useful foil: compare it with a real
semantic model (`sentence-transformers`) to *see* what embeddings add.
"""

from __future__ import annotations

import hashlib
import re
from typing import Protocol

import numpy as np

from kestrel_docs.config import Settings

_TOKEN = re.compile(r"[a-z0-9€%]+")


class Embedder(Protocol):
    dim: int

    def embed(self, texts: list[str]) -> np.ndarray: ...


class HashEmbedder:
    def __init__(self, dim: int = 384):
        self.dim = dim

    def _bucket(self, token: str) -> tuple[int, float]:
        h = hashlib.md5(token.encode()).digest()  # stable across runs (Python's hash() is salted)
        return int.from_bytes(h[:4], "little") % self.dim, 1.0 if h[4] % 2 else -1.0

    def embed(self, texts: list[str]) -> np.ndarray:
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, text in enumerate(texts):
            words = _TOKEN.findall(text.lower())
            for tok in words + [f"{a}_{b}" for a, b in zip(words, words[1:])]:
                idx, sign = self._bucket(tok)
                out[i, idx] += sign
        norms = np.linalg.norm(out, axis=1, keepdims=True)
        return out / np.where(norms == 0, 1, norms)


class SentenceTransformerEmbedder:
    """Real semantic embeddings. Install with: uv sync --extra semantic"""

    def __init__(self, model_name: str):
        from sentence_transformers import SentenceTransformer  # optional dependency

        self._model = SentenceTransformer(model_name)
        self.dim = self._model.get_sentence_embedding_dimension()

    def embed(self, texts: list[str]) -> np.ndarray:
        return np.asarray(self._model.encode(texts, normalize_embeddings=True), dtype=np.float32)


def build_embedder(settings: Settings) -> Embedder:
    if settings.embeddings_provider == "sentence-transformers":
        return SentenceTransformerEmbedder(settings.embeddings_model)
    return HashEmbedder()
