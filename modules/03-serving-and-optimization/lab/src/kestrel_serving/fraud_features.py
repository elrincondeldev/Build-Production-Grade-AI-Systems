"""Feature encoding for the fraud model, shared by training AND serving.

📖 Lesson 1.1 (training/serving skew) and 3.7 (ONNX): if the ONNX service encoded
features differently from training, it would silently score garbage. One function,
imported by both sides, removes that risk.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

MERCHANT_CATEGORIES = [
    "grocery", "restaurants", "fuel", "online_retail", "electronics",
    "travel", "gaming", "crypto_exchange", "pharmacy", "utilities",
]
NUMERIC_FEATURES = [
    "amount", "hour", "is_online", "country_mismatch", "card_age_days",
    "txn_count_24h", "avg_amount_30d", "device_is_new", "distance_from_home_km",
]
FEATURE_NAMES = NUMERIC_FEATURES + ["amount_ratio"] + [f"cat_{c}" for c in MERCHANT_CATEGORIES]


def encode(df: pd.DataFrame) -> np.ndarray:
    """DataFrame of raw transactions -> float32 matrix in FEATURE_NAMES order.

    Note what is NOT here: ``chargeback_filed`` leaks the label (📖 lesson 2.2).
    """
    numeric = df[NUMERIC_FEATURES].to_numpy(dtype=np.float32)
    ratio = (df["amount"] / df["avg_amount_30d"].clip(lower=1.0)).to_numpy(dtype=np.float32)[:, None]
    one_hot = np.stack([(df["merchant_category"] == c).to_numpy(dtype=np.float32) for c in MERCHANT_CATEGORIES], axis=1)
    return np.hstack([numeric, ratio, one_hot]).astype(np.float32)
