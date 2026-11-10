"""Tool registry: the only things the agent can do in the world.

Each tool declares whether it has side effects. Read-only tools run freely;
side-effecting tools always pass through the approval gate (lesson 6.6).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Any

from kestrel_platform.agent.ledger import Ledger
from kestrel_platform.agent.policy import check_refund_policy


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    params: tuple[str, ...]
    side_effect: bool
    fn: Callable[..., dict[str, Any]]


class ToolRegistry:
    def __init__(self, tools: list[Tool]) -> None:
        self._tools = {t.name: t for t in tools}

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise KeyError(f"unknown tool {name!r}")
        return self._tools[name]

    def names(self) -> list[str]:
        return sorted(self._tools)

    def describe(self) -> str:
        return "\n".join(
            f"- {t.name}({', '.join(t.params)}){' [SIDE EFFECT]' if t.side_effect else ''}: {t.description}"
            for t in self._tools.values()
        )

    def validate(self, name: str, args: dict[str, Any]) -> None:
        tool = self.get(name)
        missing = set(tool.params) - set(args)
        extra = set(args) - set(tool.params)
        if missing or extra:
            raise ValueError(f"bad args for {name}: missing={sorted(missing)} extra={sorted(extra)}")


def build_registry(ledger: Ledger) -> ToolRegistry:
    def lookup_transaction(transaction_id: str) -> dict[str, Any]:
        txn = ledger.get(transaction_id)
        data = asdict(txn)
        data["booked_on"] = txn.booked_on.isoformat()
        data["days_since"] = (ledger.today - txn.booked_on).days
        return data

    def check_policy(transaction_id: str) -> dict[str, Any]:
        txn = ledger.get(transaction_id)
        customer = ledger.customers[txn.customer_id]
        result = check_refund_policy(txn, customer, (ledger.today - txn.booked_on).days)
        return asdict(result)

    def issue_refund(transaction_id: str, amount_eur: float, goodwill: bool) -> dict[str, Any]:
        txn = ledger.get(transaction_id)
        if txn.refunded:
            raise RuntimeError("already refunded")  # idempotency guard: never pay twice
        if amount_eur > txn.amount_eur:
            raise ValueError("refund larger than the original charge")
        txn.refunded = True
        if goodwill:
            ledger.customers[txn.customer_id].goodwill_refunds_this_year += 1
        record = {"transaction_id": transaction_id, "amount_eur": amount_eur, "goodwill": goodwill}
        ledger.refunds.append(record)
        return {"status": "refunded", **record}

    return ToolRegistry(
        [
            Tool("lookup_transaction", "Fetch a transaction and its age in days.", ("transaction_id",), False, lookup_transaction),
            Tool("check_refund_policy", "Check the refund policy for a transaction.", ("transaction_id",), False, check_policy),
            Tool("issue_refund", "Refund money to the customer.", ("transaction_id", "amount_eur", "goodwill"), True, issue_refund),
        ]
    )
