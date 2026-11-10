"""Vector store adapter over Qdrant. 📖 Lesson 2.5 (indexing, upserts, metadata filters).

We use Qdrant's in-memory mode (`QdrantClient(":memory:")`): same API as a real
cluster, zero infrastructure. Switching to a server is one line:
`QdrantClient(url="http://localhost:6333")`.
"""

from __future__ import annotations

import uuid
import warnings
from dataclasses import dataclass

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, FieldCondition, Filter, MatchAny, PointStruct, VectorParams

from kestrel_docs.domain.chunking import Chunk

# A fixed namespace makes point IDs deterministic: same chunk_id -> same UUID, every run.
_NAMESPACE = uuid.UUID("6f1c2b1e-0d7a-4c55-9f3e-5a3b2c1d0e9f")


def point_id(chunk_id: str) -> str:
    return str(uuid.uuid5(_NAMESPACE, chunk_id))


@dataclass(frozen=True)
class VectorHit:
    chunk_id: str
    score: float


class QdrantStore:
    def __init__(self, dim: int, collection: str = "handbook", client: QdrantClient | None = None):
        self.collection = collection
        self.client = client or QdrantClient(":memory:")
        if not self.client.collection_exists(collection):
            self.client.create_collection(collection, vectors_config=VectorParams(size=dim, distance=Distance.COSINE))
            # A payload index makes filtered search fast on large collections (server mode;
            # in-memory mode ignores it and warns, which we silence).
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self.client.create_payload_index(collection, "access", field_schema="keyword")

    def upsert(self, chunks: list[Chunk], vectors: np.ndarray) -> None:
        """Insert-or-update. Re-ingesting the same chunk overwrites it instead of duplicating it."""
        points = [
            PointStruct(
                id=point_id(c.chunk_id),
                vector=v.tolist(),
                payload={"chunk_id": c.chunk_id, "doc_id": c.doc_id, "access": c.access, "section": c.section},
            )
            for c, v in zip(chunks, vectors, strict=True)
        ]
        self.client.upsert(self.collection, points=points, wait=True)

    def delete_doc(self, doc_id: str) -> None:
        """Remove every chunk of a document (needed when a doc shrinks or is deleted)."""
        self.client.delete(self.collection, points_selector=Filter(must=[FieldCondition(key="doc_id", match=MatchAny(any=[doc_id]))]))

    def count(self) -> int:
        return self.client.count(self.collection, exact=True).count

    def search(self, vector: np.ndarray, k: int, allowed_access: list[str] | None = None) -> list[VectorHit]:
        flt = None
        if allowed_access is not None:
            # The filter runs INSIDE the search, so you still get k results that pass it.
            flt = Filter(must=[FieldCondition(key="access", match=MatchAny(any=allowed_access))])
        res = self.client.query_points(self.collection, query=vector.tolist(), limit=k, query_filter=flt, with_payload=True)
        return [VectorHit(p.payload["chunk_id"], float(p.score)) for p in res.points]
