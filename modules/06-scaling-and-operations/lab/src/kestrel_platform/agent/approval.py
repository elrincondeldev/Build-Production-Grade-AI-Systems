"""Human-in-the-loop (HITL) approval gate.

Two separate questions:
1. The *gate* (policy): does this action need a human? AUTO, REQUIRE_APPROVAL or REFUSE.
2. The *approver* (channel): how do we ask a human? CLI prompt, approvals file, or
   a safe default that denies.

Keeping them separate means you can change who approves (Slack, a ticket queue)
without touching the rules about what needs approving.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Protocol

AUTONOMY_LIMIT_EUR = 50.0


class GateDecision(str, Enum):
    AUTO = "auto"
    REQUIRE_APPROVAL = "require_approval"
    REFUSE = "refuse"


@dataclass(frozen=True)
class GateResult:
    decision: GateDecision
    reason: str


def gate_refund(amount_eur: float, policy: dict[str, Any], autonomy_limit_eur: float = AUTONOMY_LIMIT_EUR) -> GateResult:
    """Rules for the one side-effecting tool, issue_refund."""
    if policy.get("hard_block"):
        return GateResult(GateDecision.REFUSE, "policy hard block: " + "; ".join(policy.get("reasons", [])))
    if not policy.get("eligible"):
        return GateResult(GateDecision.REQUIRE_APPROVAL, "goodwill refund outside standard policy: " + "; ".join(policy.get("reasons", [])))
    if amount_eur > autonomy_limit_eur:
        return GateResult(GateDecision.REQUIRE_APPROVAL, f"amount €{amount_eur:.2f} is above the €{autonomy_limit_eur:.0f} autonomy limit")
    return GateResult(GateDecision.AUTO, "eligible and within the autonomy limit")


@dataclass(frozen=True)
class ApprovalRequest:
    tool: str
    args: dict[str, Any]
    reason: str

    @property
    def request_id(self) -> str:
        """Deterministic id: the same action always maps to the same approval."""
        raw = json.dumps({"tool": self.tool, "args": self.args}, sort_keys=True)
        return "apr_" + hashlib.sha256(raw.encode()).hexdigest()[:10]


class ApprovalStatus(str, Enum):
    APPROVED = "approved"
    DENIED = "denied"
    PENDING = "pending"


class Approver(Protocol):
    def request(self, req: ApprovalRequest) -> ApprovalStatus: ...


class AutoDenyApprover:
    """The safe default when no human is reachable: do nothing risky."""

    def request(self, req: ApprovalRequest) -> ApprovalStatus:
        return ApprovalStatus.DENIED


class AutoApproveApprover:
    """For tests and demos only. Never wire this up in production."""

    def request(self, req: ApprovalRequest) -> ApprovalStatus:
        return ApprovalStatus.APPROVED


class CLIApprover:
    def request(self, req: ApprovalRequest) -> ApprovalStatus:
        print(f"\n🙋 APPROVAL NEEDED [{req.request_id}] {req.tool}({req.args})\n   reason: {req.reason}")
        answer = input("   approve? [y/N] ").strip().lower()
        return ApprovalStatus.APPROVED if answer in ("y", "yes") else ApprovalStatus.DENIED


class FileApprover:
    """Asynchronous approvals through a JSON file: {"apr_...": "approve" | "deny"}.

    Unknown requests are written to `<file>.pending.json` and the run stops with
    status "awaiting_approval". A human edits the approvals file and re-runs.
    This is the shape of real HITL systems: the agent pauses, it does not block a thread.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self.pending_path = path.with_suffix(".pending.json")

    def _load(self, path: Path) -> dict[str, Any]:
        return json.loads(path.read_text()) if path.exists() else {}

    def request(self, req: ApprovalRequest) -> ApprovalStatus:
        decision = self._load(self.path).get(req.request_id)
        if decision == "approve":
            return ApprovalStatus.APPROVED
        if decision == "deny":
            return ApprovalStatus.DENIED
        pending = self._load(self.pending_path)
        pending[req.request_id] = {"tool": req.tool, "args": req.args, "reason": req.reason}
        self.pending_path.write_text(json.dumps(pending, indent=2))
        return ApprovalStatus.PENDING
