"""A tiny, dependency-free fraud scorer.

Module 6 is about *operating* the service, not modelling, so the scorer is a
transparent logistic function. In Module 1 you served a trained artifact; the
operational patterns here (probes, canaries, HPA) are identical either way.
"""

from __future__ import annotations

import math

from pydantic import BaseModel, Field

RISKY_CATEGORIES = {"electronics": 0.9, "gaming": 0.8, "crypto_exchange": 1.4, "travel": 0.6, "online_retail": 0.5}


class Transaction(BaseModel):
    amount: float = Field(gt=0)
    merchant_category: str
    hour: int = Field(ge=0, le=23)
    is_online: bool = False
    country_mismatch: bool = False
    device_is_new: bool = False
    avg_amount_30d: float = Field(default=30.0, gt=0)


class Score(BaseModel):
    fraud_probability: float
    decision: str  # approve | review | decline
    model_version: str


def score(txn: Transaction, model_version: str, review_at: float = 0.2, decline_at: float = 0.6) -> Score:
    ratio = txn.amount / txn.avg_amount_30d
    z = -5.5
    z += RISKY_CATEGORIES.get(txn.merchant_category, -0.4)
    z += 0.9 * math.log1p(ratio)
    z += 1.3 * txn.country_mismatch + 1.1 * txn.device_is_new + 0.5 * txn.is_online
    z += 0.9 if txn.hour <= 4 else 0.0
    p = 1 / (1 + math.exp(-z))
    decision = "decline" if p >= decline_at else "review" if p >= review_at else "approve"
    return Score(fraud_probability=round(p, 4), decision=decision, model_version=model_version)
