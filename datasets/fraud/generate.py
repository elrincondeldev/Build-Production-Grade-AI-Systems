"""Generate the synthetic Kestrel Pay card-transaction dataset.

Why synthetic?  Real fraud datasets need sign-ups, have restrictive licences or
anonymised features you cannot reason about. This generator produces readable
features with a known ground truth, so you can *see* leakage, drift and
calibration problems instead of guessing.

Usage (no dependencies beyond the standard library):

    python datasets/fraud/generate.py                      # baseline -> transactions.csv
    python datasets/fraud/generate.py --rows 5000 --seed 7 --out /tmp/t.csv
    python datasets/fraud/generate.py --scenario data_drift    # inputs shift
    python datasets/fraud/generate.py --scenario concept_drift # fraud pattern changes

Scenarios (used in Module 4, lesson 4.5 "Drift and alerting"):
    baseline       the world the model is trained on
    data_drift     P(X) changes: more online spend, bigger amounts, more travel
    concept_drift  P(y|X) changes: fraudsters switch to "card testing"
                   (many tiny amounts) that the baseline model has never seen
"""

from __future__ import annotations

import argparse
import csv
import math
import random
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timedelta
from pathlib import Path

MERCHANT_CATEGORIES = [
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
]

# Baseline share of transactions per category (sums to 1.0).
BASELINE_CATEGORY_WEIGHTS = [0.22, 0.16, 0.10, 0.18, 0.06, 0.05, 0.05, 0.02, 0.08, 0.08]
DATA_DRIFT_CATEGORY_WEIGHTS = [0.14, 0.12, 0.07, 0.30, 0.10, 0.10, 0.07, 0.03, 0.04, 0.03]

# How "risky" each category is for the hidden fraud function.
CATEGORY_RISK = {
    "grocery": -0.6,
    "restaurants": -0.4,
    "fuel": -0.2,
    "online_retail": 0.5,
    "electronics": 0.9,
    "travel": 0.6,
    "gaming": 0.8,
    "crypto_exchange": 1.4,
    "pharmacy": -0.5,
    "utilities": -0.9,
}

COUNTRIES = ["ES", "PT", "FR", "DE", "IT", "GB", "US", "MX", "BR", "NG"]


@dataclass
class Transaction:
    transaction_id: str
    timestamp: str
    customer_id: str
    amount: float
    merchant_category: str
    hour: int
    is_online: int
    country: str
    country_mismatch: int  # card country != transaction country
    card_age_days: int
    txn_count_24h: int
    avg_amount_30d: float
    device_is_new: int
    distance_from_home_km: float
    # ⚠️ LEAKY FEATURE (on purpose, see lesson 2.2): this field is only filled in
    # *after* an investigation, i.e. after the label is known. It must never be
    # used for training. It exists so you can practise catching leakage.
    chargeback_filed: int
    is_fraud: int


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _fraud_logit(t: Transaction, scenario: str) -> float:
    """Hidden ground-truth function. Models must *learn* this, never read it."""
    ratio = t.amount / max(t.avg_amount_30d, 1.0)
    z = -6.2
    z += CATEGORY_RISK[t.merchant_category]
    z += 0.9 * math.log1p(ratio)
    z += 1.3 * t.country_mismatch
    z += 1.1 * t.device_is_new
    z += 0.5 * t.is_online
    z += 0.04 * min(t.txn_count_24h, 30)
    z += 0.9 if t.hour in (0, 1, 2, 3, 4) else 0.0
    z += 0.8 if t.card_age_days < 30 else 0.0
    z += 0.35 * math.log1p(t.distance_from_home_km / 100)

    if scenario == "concept_drift":
        # Card testing: many tiny online charges in a short window are now fraud,
        # a pattern that was benign in the baseline world.
        if t.amount < 3.0 and t.is_online and t.txn_count_24h >= 8:
            z += 5.0
    return z


def _make_transaction(rng: random.Random, i: int, start: datetime, scenario: str) -> Transaction:
    weights = DATA_DRIFT_CATEGORY_WEIGHTS if scenario == "data_drift" else BASELINE_CATEGORY_WEIGHTS
    category = rng.choices(MERCHANT_CATEGORIES, weights=weights, k=1)[0]

    customer = rng.randint(1, 4000)
    avg_30d = round(rng.lognormvariate(3.4, 0.6), 2)  # ~30 EUR typical
    amount_scale = 1.6 if scenario == "data_drift" else 1.0
    amount = round(rng.lognormvariate(math.log(avg_30d), 0.9) * amount_scale, 2)

    is_online = int(category in ("online_retail", "gaming", "crypto_exchange") or rng.random() < 0.15)
    travel_rate = 0.12 if scenario == "data_drift" else 0.05
    mismatch = int(rng.random() < travel_rate)
    country = rng.choice(COUNTRIES[1:]) if mismatch else "ES"
    hour = int(rng.triangular(0, 23, 15))
    txn_24h = max(0, int(rng.gauss(4, 2.5)))

    if scenario == "concept_drift" and rng.random() < 0.03:
        # inject card-testing bursts
        amount = round(rng.uniform(0.5, 2.99), 2)
        is_online = 1
        txn_24h = rng.randint(8, 25)

    t = Transaction(
        transaction_id=f"txn_{i:07d}",
        timestamp=(start + timedelta(seconds=i * 37)).isoformat(timespec="seconds"),
        customer_id=f"cus_{customer:05d}",
        amount=amount,
        merchant_category=category,
        hour=hour,
        is_online=is_online,
        country=country,
        country_mismatch=mismatch,
        card_age_days=int(rng.expovariate(1 / 700)),
        txn_count_24h=txn_24h,
        avg_amount_30d=avg_30d,
        device_is_new=int(rng.random() < 0.08),
        distance_from_home_km=round(rng.expovariate(1 / 15) + (800 if mismatch else 0), 1),
        chargeback_filed=0,
        is_fraud=0,
    )
    t.is_fraud = int(rng.random() < _sigmoid(_fraud_logit(t, scenario)))
    # Leakage: chargebacks are filed for ~85% of fraud and ~0.5% of legit txns.
    t.chargeback_filed = int(rng.random() < (0.85 if t.is_fraud else 0.005))
    return t


def generate(rows: int, seed: int, scenario: str) -> list[Transaction]:
    rng = random.Random(seed)
    start = datetime(2026, 1, 1) if scenario == "baseline" else datetime(2026, 9, 1)
    return [_make_transaction(rng, i, start, scenario) for i in range(rows)]


def write_csv(transactions: list[Transaction], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=[f.name for f in fields(Transaction)])
        writer.writeheader()
        for t in transactions:
            writer.writerow(asdict(t))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rows", type=int, default=50_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--scenario", choices=["baseline", "data_drift", "concept_drift"], default="baseline")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    out = args.out or Path(__file__).parent / (
        "transactions.csv" if args.scenario == "baseline" else f"transactions_{args.scenario}.csv"
    )
    data = generate(args.rows, args.seed, args.scenario)
    write_csv(data, out)
    fraud_rate = sum(t.is_fraud for t in data) / len(data)
    print(f"wrote {len(data):,} rows to {out}  (scenario={args.scenario}, fraud rate={fraud_rate:.2%})")


if __name__ == "__main__":
    main()
