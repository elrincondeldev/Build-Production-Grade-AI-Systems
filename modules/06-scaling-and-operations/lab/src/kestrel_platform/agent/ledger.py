"""A tiny in-memory ledger standing in for Kestrel's payments database.

Fixed dates make every run deterministic: "today" is 2026-11-10 unless you pass another date.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

TODAY = date(2026, 11, 10)


@dataclass
class LedgerTransaction:
    transaction_id: str
    customer_id: str
    booked_on: date
    kind: str  # card_fee | account_fee | premium_fee | atm_third_party_fee | fx_markup | purchase
    amount_eur: float
    description: str
    fx_markup_over_reference_pct: float = 0.0  # only for kind == fx_markup
    refunded: bool = False


@dataclass
class Customer:
    customer_id: str
    name: str
    goodwill_refunds_this_year: int = 0


@dataclass
class Ledger:
    today: date = TODAY
    customers: dict[str, Customer] = field(default_factory=dict)
    transactions: dict[str, LedgerTransaction] = field(default_factory=dict)
    refunds: list[dict[str, object]] = field(default_factory=list)

    def get(self, transaction_id: str) -> LedgerTransaction:
        if transaction_id not in self.transactions:
            raise KeyError(f"unknown transaction {transaction_id}")
        return self.transactions[transaction_id]


def demo_ledger() -> Ledger:
    """Four customers, one per lesson scenario (see scripts/run_agent.py)."""
    customers = [
        Customer("cus_ana", "Ana (fictional)", goodwill_refunds_this_year=0),
        Customer("cus_ben", "Ben (fictional)", goodwill_refunds_this_year=1),
        Customer("cus_chloe", "Chloe (fictional)", goodwill_refunds_this_year=0),
        Customer("cus_dev", "Dev (fictional)", goodwill_refunds_this_year=3),
    ]
    txns = [
        # 1. small fee, inside the 60-day window -> agent refunds on its own
        LedgerTransaction("txn_fee_small", "cus_ana", date(2026, 10, 28), "card_fee", 7.00, "Card replacement fee"),
        # 2. inside the window but above the EUR 50 autonomy limit -> human approval
        LedgerTransaction("txn_fee_large", "cus_ben", date(2026, 10, 20), "account_fee", 79.00, "Annual account fee"),
        # 3. outside the 60-day window -> only possible as a goodwill refund -> human approval
        LedgerTransaction("txn_fee_old", "cus_chloe", date(2026, 8, 1), "card_fee", 12.99, "Premium plan fee"),
        # 4. outside the window and goodwill limit already used -> refused, no override
        LedgerTransaction("txn_fee_blocked", "cus_dev", date(2026, 7, 15), "card_fee", 9.50, "Card fee"),
        # 5. third-party ATM fee -> never refundable by Kestrel
        LedgerTransaction("txn_atm", "cus_ana", date(2026, 11, 1), "atm_third_party_fee", 2.50, "ATM operator fee"),
        # 6. FX markup only 1.1% above reference -> not eligible by rule, goodwill possible
        LedgerTransaction("txn_fx", "cus_ana", date(2026, 11, 2), "fx_markup", 4.10, "FX markup", 1.1),
    ]
    return Ledger(customers={c.customer_id: c for c in customers}, transactions={t.transaction_id: t for t in txns})
