"""Feature engineering shared by training AND serving (📖 lessons 1.1 and 2.2).

This one module is the cure for training/serving skew. Sam's notebook built
features with ``pd.get_dummies`` at training time and a hand-written dict at
prediction time. The two drifted apart and nobody noticed. Here there is exactly
one function, ``build_feature_vector``, imported by ``training.py`` and by the API.

``FEATURE_NAMES`` is written into the artifact's metadata.json. At load time the
service refuses to start if the artifact was trained on a different feature list.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

FEATURE_SPEC_VERSION = "1"

MERCHANT_CATEGORIES: tuple[str, ...] = (
    "grocery",
    "restaurants",
    "fuel",
    "online_retail",
    "electronics",
    "travel",
    "gaming",
    "crypto_exchange",
    "pharmacy",
    "utilities",
)

# Columns from the raw dataset that must NEVER be used as features.
# chargeback_filed is only known weeks after the transaction: it leaks the label.
FORBIDDEN_COLUMNS: frozenset[str] = frozenset({"chargeback_filed", "is_fraud", "transaction_id"})

NUMERIC_FEATURES: tuple[str, ...] = (
    "amount_log",
    "amount_to_avg_ratio_log",
    "hour",
    "is_night",
    "is_online",
    "country_mismatch",
    "card_age_days_log",
    "is_new_card",
    "txn_count_24h",
    "device_is_new",
    "distance_from_home_log",
)

FEATURE_NAMES: tuple[str, ...] = NUMERIC_FEATURES + tuple(f"merchant_category={c}" for c in MERCHANT_CATEGORIES)


class InvalidTransaction(ValueError):
    """Raised when a transaction cannot be turned into features."""


@dataclass(frozen=True, slots=True)
class Transaction:
    """What the model needs to know about one card transaction."""

    transaction_id: str
    customer_id: str
    amount: float
    merchant_category: str
    hour: int
    is_online: bool
    country_mismatch: bool
    card_age_days: int
    device_is_new: bool
    distance_from_home_km: float
    # Customer aggregates usually come from the online feature store (enrichment).
    txn_count_24h: int | None = None
    avg_amount_30d: float | None = None


# Population medians used when enrichment is unavailable (graceful degradation).
DEFAULT_TXN_COUNT_24H = 4
DEFAULT_AVG_AMOUNT_30D = 30.0


def validate(txn: Transaction) -> None:
    """Business validation the type system cannot express."""
    if txn.merchant_category not in MERCHANT_CATEGORIES:
        raise InvalidTransaction(f"unknown merchant_category {txn.merchant_category!r}")
    if not 0 <= txn.hour <= 23:
        raise InvalidTransaction("hour must be in 0..23")
    if txn.amount <= 0:
        raise InvalidTransaction("amount must be positive")
    if txn.card_age_days < 0 or txn.distance_from_home_km < 0:
        raise InvalidTransaction("card_age_days and distance_from_home_km must be >= 0")


def build_feature_vector(txn: Transaction) -> list[float]:
    """Turn one transaction into the model's input row, in FEATURE_NAMES order."""
    validate(txn)
    txn_count = txn.txn_count_24h if txn.txn_count_24h is not None else DEFAULT_TXN_COUNT_24H
    avg_amount = txn.avg_amount_30d if txn.avg_amount_30d is not None else DEFAULT_AVG_AMOUNT_30D

    numeric = [
        math.log1p(txn.amount),
        math.log1p(txn.amount / max(avg_amount, 1.0)),
        float(txn.hour),
        1.0 if txn.hour < 5 else 0.0,
        float(txn.is_online),
        float(txn.country_mismatch),
        math.log1p(txn.card_age_days),
        1.0 if txn.card_age_days < 30 else 0.0,
        float(min(txn_count, 50)),
        float(txn.device_is_new),
        math.log1p(txn.distance_from_home_km),
    ]
    one_hot = [1.0 if txn.merchant_category == c else 0.0 for c in MERCHANT_CATEGORIES]
    row = numeric + one_hot
    assert len(row) == len(FEATURE_NAMES)  # cheap guard against silent column drift
    return row


def transaction_from_csv_row(row: dict[str, str]) -> Transaction:
    """Parse one row of datasets/fraud/transactions.csv (used by training)."""
    return Transaction(
        transaction_id=row["transaction_id"],
        customer_id=row["customer_id"],
        amount=float(row["amount"]),
        merchant_category=row["merchant_category"],
        hour=int(row["hour"]),
        is_online=row["is_online"] == "1",
        country_mismatch=row["country_mismatch"] == "1",
        card_age_days=int(row["card_age_days"]),
        device_is_new=row["device_is_new"] == "1",
        distance_from_home_km=float(row["distance_from_home_km"]),
        txn_count_24h=int(row["txn_count_24h"]),
        avg_amount_30d=float(row["avg_amount_30d"]),
    )
