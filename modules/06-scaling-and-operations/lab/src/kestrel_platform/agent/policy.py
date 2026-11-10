"""Refund policy as code.

Source of truth: datasets/handbook/refund-policy.md. A test
(tests/test_agent.py::test_policy_constants_match_handbook) fails if the handbook and
these constants drift apart: policy-as-code needs a link back to the policy-as-prose.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from kestrel_platform.agent.ledger import Customer, LedgerTransaction

REFUND_WINDOW_DAYS = 60
MAX_GOODWILL_REFUNDS_PER_YEAR = 3
FX_MARKUP_THRESHOLD_PCT = 2.0
REFUNDABLE_KINDS = {"card_fee", "account_fee", "premium_fee", "fx_markup"}


@dataclass
class PolicyResult:
    eligible: bool  # refundable under the normal rules
    goodwill_possible: bool  # could be granted as a goodwill refund by a team lead
    hard_block: bool  # nobody may refund this through the agent
    reasons: list[str] = field(default_factory=list)


def check_refund_policy(txn: LedgerTransaction, customer: Customer, today_days_since: int) -> PolicyResult:
    reasons: list[str] = []
    if txn.refunded:
        return PolicyResult(False, False, True, ["already refunded"])
    if txn.kind == "purchase":
        return PolicyResult(False, False, True, ["purchases are disputed with the merchant (card dispute process)"])
    if txn.kind == "atm_third_party_fee":
        return PolicyResult(False, False, True, ["third-party ATM fees are not refundable by Kestrel Pay"])
    if txn.kind not in REFUNDABLE_KINDS:
        return PolicyResult(False, False, True, [f"unknown charge type {txn.kind!r}"])

    eligible = True
    if today_days_since > REFUND_WINDOW_DAYS:
        eligible = False
        reasons.append(f"charge is {today_days_since} days old (window is {REFUND_WINDOW_DAYS} days)")
    if txn.kind == "fx_markup" and txn.fx_markup_over_reference_pct <= FX_MARKUP_THRESHOLD_PCT:
        eligible = False
        reasons.append(
            f"FX markup {txn.fx_markup_over_reference_pct}% is not more than {FX_MARKUP_THRESHOLD_PCT}% above reference"
        )
    if eligible:
        return PolicyResult(True, False, False, ["eligible under the standard rules"])

    if customer.goodwill_refunds_this_year >= MAX_GOODWILL_REFUNDS_PER_YEAR:
        reasons.append(
            f"goodwill limit reached ({customer.goodwill_refunds_this_year}/{MAX_GOODWILL_REFUNDS_PER_YEAR} this year)"
        )
        return PolicyResult(False, False, True, reasons)
    reasons.append("only possible as a goodwill refund (team lead discretion)")
    return PolicyResult(False, True, False, reasons)
