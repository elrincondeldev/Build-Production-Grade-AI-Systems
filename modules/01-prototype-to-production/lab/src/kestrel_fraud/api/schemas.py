"""Request/response contracts (📖 lesson 1.4).

These Pydantic models are the service's public API. FastAPI validates every
request against them and returns 422 with a precise error if a field is wrong,
before your code runs. They also generate the OpenAPI docs at /docs.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ..domain.features import MERCHANT_CATEGORIES, Transaction
from ..domain.scoring import ScoreResult

MerchantCategory = Literal[MERCHANT_CATEGORIES]  # type: ignore[valid-type]


class ScoreRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",  # unknown fields are an error, not silently ignored
        json_schema_extra={
            "example": {
                "transaction_id": "txn_0000042",
                "customer_id": "cus_00017",
                "amount": 249.99,
                "merchant_category": "electronics",
                "hour": 2,
                "is_online": True,
                "country_mismatch": True,
                "card_age_days": 12,
                "device_is_new": True,
                "distance_from_home_km": 912.4,
            }
        },
    )

    transaction_id: str = Field(min_length=1, max_length=64)
    customer_id: str = Field(min_length=1, max_length=64)
    amount: float = Field(gt=0, le=1_000_000, description="Amount in EUR")
    merchant_category: MerchantCategory
    hour: int = Field(ge=0, le=23)
    is_online: bool
    country_mismatch: bool
    card_age_days: int = Field(ge=0)
    device_is_new: bool
    distance_from_home_km: float = Field(ge=0)
    txn_count_24h: int | None = Field(None, ge=0, description="Optional: fetched from the feature store if absent")
    avg_amount_30d: float | None = Field(None, gt=0, description="Optional: fetched from the feature store if absent")

    def to_domain(self) -> Transaction:
        return Transaction(**self.model_dump())


class ScoreResponse(BaseModel):
    transaction_id: str
    score: float = Field(ge=0, le=1, description="Estimated probability of fraud")
    decision: Literal["approve", "review", "decline"]
    source: Literal["model", "rules"]
    model_version: str | None
    reasons: list[str]
    degraded: bool
    degraded_reasons: list[str]
    request_id: str | None

    @classmethod
    def from_result(cls, r: ScoreResult, request_id: str | None) -> ScoreResponse:
        return cls(
            transaction_id=r.transaction_id,
            score=r.score,
            decision=r.decision,
            source=r.source,
            model_version=r.model_version,
            reasons=r.reasons,
            degraded=bool(r.degraded_reasons),
            degraded_reasons=r.degraded_reasons,
            request_id=request_id,
        )


class HealthResponse(BaseModel):
    status: Literal["ok"]


class ReadyResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    model_version: str | None
    reason: str | None = None
