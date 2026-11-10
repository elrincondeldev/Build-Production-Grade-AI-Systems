"""Use-case orchestration: enrich → score (📖 lesson 1.3).

The service depends on a *port* (``CustomerFeatureSource``), not on httpx. In
production the port is an HTTP client for the online feature store; in tests it
can be a dict. If enrichment fails, we degrade gracefully instead of failing the
payment: we score with population defaults and flag the response as degraded.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Protocol

from .features import Transaction
from .scoring import FraudScorer, ScoreResult


class EnrichmentUnavailable(Exception):
    """The feature source could not answer in time (after retries)."""


class CustomerFeatureSource(Protocol):
    async def get_customer_features(self, customer_id: str) -> dict[str, float]: ...


class ScoringService:
    def __init__(self, scorer: FraudScorer, features: CustomerFeatureSource | None):
        self.scorer = scorer
        self.features = features

    async def score(self, txn: Transaction) -> ScoreResult:
        degraded: list[str] = []
        needs_enrichment = txn.txn_count_24h is None or txn.avg_amount_30d is None
        if needs_enrichment:
            if self.features is None:
                degraded.append("enrichment_disabled")
            else:
                try:
                    feats = await self.features.get_customer_features(txn.customer_id)
                    txn = replace(
                        txn,
                        txn_count_24h=txn.txn_count_24h if txn.txn_count_24h is not None else int(feats["txn_count_24h"]),
                        avg_amount_30d=txn.avg_amount_30d if txn.avg_amount_30d is not None else float(feats["avg_amount_30d"]),
                    )
                except EnrichmentUnavailable:
                    degraded.append("enrichment_unavailable")
        return self.scorer.score(txn, degraded_reasons=degraded)
