"""Scoring and decision policy (📖 lessons 1.3 and 1.4).

The domain does not know what scikit-learn is. It only needs *something* with a
``predict_proba`` method, which is described by the ``ProbabilisticModel`` protocol.
That makes the domain testable with a 3-line fake and lets you swap the model
runtime (sklearn → ONNX Runtime in Module 3) without touching business rules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol, Sequence

from .features import Transaction, build_feature_vector

Decision = Literal["approve", "review", "decline"]
Source = Literal["model", "rules"]

HIGH_RISK_CATEGORIES = frozenset({"crypto_exchange", "gaming", "electronics"})


class ProbabilisticModel(Protocol):
    def predict_proba(self, rows: Sequence[Sequence[float]]) -> Sequence[Sequence[float]]: ...


@dataclass(frozen=True)
class DecisionPolicy:
    review_threshold: float = 0.30
    decline_threshold: float = 0.80

    def decide(self, score: float) -> Decision:
        if score >= self.decline_threshold:
            return "decline"
        if score >= self.review_threshold:
            return "review"
        return "approve"


@dataclass
class ScoreResult:
    transaction_id: str
    score: float
    decision: Decision
    source: Source
    model_version: str | None
    reasons: list[str] = field(default_factory=list)
    degraded_reasons: list[str] = field(default_factory=list)


def risk_reasons(txn: Transaction) -> list[str]:
    """Human-readable risk signals. Used by the fallback and by /v1/explain."""
    reasons: list[str] = []
    avg = txn.avg_amount_30d or 30.0
    if txn.country_mismatch:
        reasons.append("transaction country differs from card country")
    if txn.device_is_new:
        reasons.append("first time this device is seen for the customer")
    if txn.hour < 5:
        reasons.append("transaction at night (00:00-04:59)")
    if txn.merchant_category in HIGH_RISK_CATEGORIES:
        reasons.append(f"high-risk merchant category ({txn.merchant_category})")
    if txn.amount / max(avg, 1.0) > 5:
        reasons.append(f"amount is {txn.amount / max(avg, 1.0):.1f}x the customer's 30-day average")
    if txn.card_age_days < 30:
        reasons.append("card issued less than 30 days ago")
    if (txn.txn_count_24h or 0) >= 15:
        reasons.append("unusually many transactions in the last 24h")
    return reasons


def rule_based_score(txn: Transaction) -> float:
    """Fallback score when the model is unavailable (graceful degradation, lesson 1.3).

    Deliberately simple and conservative: it is worse than the model, but it is
    always available, has no dependencies, and every risk analyst can read it.
    """
    weights = {
        "transaction country differs": 0.25,
        "first time this device": 0.20,
        "transaction at night": 0.10,
        "high-risk merchant": 0.15,
        "amount is": 0.20,
        "card issued less": 0.10,
        "unusually many": 0.10,
    }
    score = 0.02
    for reason in risk_reasons(txn):
        score += next(w for prefix, w in weights.items() if reason.startswith(prefix))
    return round(min(score, 0.99), 4)


class FraudScorer:
    """Scores one transaction with the model, or with rules if there is no model."""

    def __init__(self, model: ProbabilisticModel | None, model_version: str | None, policy: DecisionPolicy):
        self.model = model
        self.model_version = model_version
        self.policy = policy

    @property
    def has_model(self) -> bool:
        return self.model is not None

    def score(self, txn: Transaction, degraded_reasons: list[str] | None = None) -> ScoreResult:
        degraded = list(degraded_reasons or [])
        if self.model is not None:
            row = build_feature_vector(txn)
            # predict_proba is CPU-bound and takes well under 1 ms for this model.
            # For a heavy model you would run it in a thread pool (lesson 1.4).
            score = float(self.model.predict_proba([row])[0][1])
            source: Source = "model"
            version = self.model_version
        else:
            score = rule_based_score(txn)
            source = "rules"
            version = None
            degraded.append("model_unavailable")
        return ScoreResult(
            transaction_id=txn.transaction_id,
            score=round(score, 4),
            decision=self.policy.decide(score),
            source=source,
            model_version=version,
            reasons=risk_reasons(txn),
            degraded_reasons=degraded,
        )
