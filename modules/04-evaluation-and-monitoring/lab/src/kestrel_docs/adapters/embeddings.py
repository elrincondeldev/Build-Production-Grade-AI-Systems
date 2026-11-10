"""Embedding providers.

``hash`` (default): the "hashing trick". Each token is hashed into one of
``dim`` buckets and the vector is L2-normalised. No download, deterministic,
good enough to *demonstrate* embedding drift. Similar texts share tokens, so
they get similar vectors.

``sentence-transformers`` (optional extra): real semantic embeddings, e.g.
``all-MiniLM-L6-v2``. Install with ``uv pip install sentence-transformers``.
"""

from __future__ import annotations

import hashlib
from typing import Protocol

import numpy as np

from kestrel_docs.domain.text import content_tokens


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> np.ndarray: ...


class HashEmbedder:
    def __init__(self, dim: int = 256) -> None:
        self.dim = dim

    def _bucket(self, token: str) -> int:
        digest = hashlib.blake2b(token.encode(), digest_size=8).digest()
        return int.from_bytes(digest, "little") % self.dim

    def embed(self, texts: list[str]) -> np.ndarray:
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, text in enumerate(texts):
            for tok in content_tokens(text):
                out[i, self._bucket(tok)] += 1.0
        norms = np.linalg.norm(out, axis=1, keepdims=True)
        return out / np.where(norms == 0, 1.0, norms)


class SentenceTransformerEmbedder:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        from sentence_transformers import SentenceTransformer  # optional dependency

        self._model = SentenceTransformer(model_name)

    def embed(self, texts: list[str]) -> np.ndarray:
        return np.asarray(self._model.encode(texts, normalize_embeddings=True), dtype=np.float32)


def build_embedder(provider: str = "hash") -> Embedder:
    if provider == "sentence-transformers":
        return SentenceTransformerEmbedder()
    return HashEmbedder()
