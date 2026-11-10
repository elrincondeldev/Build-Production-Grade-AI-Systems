"""The worker loop: plan -> gate -> (approve) -> execute -> observe, with hard limits.

Production rules encoded here (lesson 6.6):
* every step is traced;
* the loop has a step limit and a money budget, enforced in code, not in the prompt;
* side-effecting tools go through the approval gate;
* "no human answered" means "do not act".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from kestrel_platform.agent.approval import (
    ApprovalRequest,
    ApprovalStatus,
    Approver,
    AutoDenyApprover,
    GateDecision,
    gate_refund,
)
from kestrel_platform.agent.planner import AgentState, Finish, Planner, RulePlanner, Step
from kestrel_platform.agent.tools import ToolRegistry
from kestrel_platform.agent.trace import Tracer


@dataclass(frozen=True)
class Task:
    transaction_id: str
    reason: str = "customer requested a fee refund"


@dataclass(frozen=True)
class Limits:
    max_steps: int = 8
    max_refund_total_eur: float = 500.0


@dataclass
class RunResult:
    status: str  # completed | refused | denied_by_human | awaiting_approval | stopped_max_steps | stopped_budget | failed
    message: str
    steps: int
    tracer: Tracer
    approvals: list[dict[str, Any]] = field(default_factory=list)


class AgentRunner:
    def __init__(
        self,
        registry: ToolRegistry,
        planner: Planner | None = None,
        approver: Approver | None = None,
        limits: Limits | None = None,
    ) -> None:
        self.registry = registry
        self.planner = planner or RulePlanner()
        self.approver = approver or AutoDenyApprover()
        self.limits = limits or Limits()
        self.refunded_total = 0.0

    def run(self, task: Task) -> RunResult:
        tracer = Tracer()
        state = AgentState(task={"transaction_id": task.transaction_id, "reason": task.reason})
        approvals: list[dict[str, Any]] = []
        steps = 0

        def finish(status: str, message: str) -> RunResult:
            root.set(status=status, steps=steps)
            return RunResult(status, message, steps, tracer, approvals)

        with tracer.span("agent.run", transaction_id=task.transaction_id, planner=self.planner.name) as root:
            while True:
                if steps >= self.limits.max_steps:
                    root.event("limit_hit", limit="max_steps", value=self.limits.max_steps)
                    return finish("stopped_max_steps", f"stopped after {steps} steps without finishing")

                with tracer.span("planner.next_step", step=steps + 1) as ps:
                    decision = self.planner.next_step(state)
                    if getattr(self.planner, "last_used_fallback", False):
                        ps.event("planner_fallback", reason="invalid LLM output")
                    ps.set(decision=type(decision).__name__)

                if isinstance(decision, Finish):
                    return finish(decision.status, decision.message)

                steps += 1
                step: Step = decision
                try:
                    self.registry.validate(step.tool, step.args)
                except (KeyError, ValueError) as exc:
                    root.event("invalid_step", error=str(exc))
                    return finish("failed", str(exc))
                tool = self.registry.get(step.tool)

                if tool.side_effect:
                    blocked = self._gate(step, state, tracer, approvals)
                    if blocked is not None:
                        return finish(*blocked)

                with tracer.span(f"tool.{step.tool}", **{f"arg.{k}": v for k, v in step.args.items()}) as ts:
                    try:
                        result = tool.fn(**step.args)
                    except Exception as exc:  # tool failures end the run, they don't loop forever
                        ts.status = "error"
                        ts.event("exception", message=str(exc))
                        return finish("failed", f"{step.tool} failed: {exc}")
                if step.tool == "issue_refund":
                    self.refunded_total += float(step.args["amount_eur"])
                state.observations[step.tool] = result
                state.history.append(step)

    def _gate(
        self, step: Step, state: AgentState, tracer: Tracer, approvals: list[dict[str, Any]]
    ) -> tuple[str, str] | None:
        """Return (status, message) to stop the run, or None to let the step execute."""
        amount = float(step.args.get("amount_eur", 0.0))
        with tracer.span("approval.gate", tool=step.tool, amount_eur=amount) as gs:
            if self.refunded_total + amount > self.limits.max_refund_total_eur:
                gs.set(decision="budget_exceeded")
                return "stopped_budget", f"refund budget of €{self.limits.max_refund_total_eur:.0f} per run exceeded"
            policy = state.observations.get("check_refund_policy")
            if policy is None:
                gs.set(decision="refuse")
                return "refused", "refusing to issue a refund before checking the policy"
            gate = gate_refund(amount, policy)
            gs.set(decision=gate.decision.value, reason=gate.reason)
            if gate.decision is GateDecision.REFUSE:
                return "refused", gate.reason
            if gate.decision is GateDecision.AUTO:
                return None
            req = ApprovalRequest(step.tool, step.args, gate.reason)
            status = self.approver.request(req)
            approvals.append({"request_id": req.request_id, "reason": req.reason, "status": status.value})
            gs.event("approval", request_id=req.request_id, status=status.value, approver=type(self.approver).__name__)
            if status is ApprovalStatus.APPROVED:
                return None
            if status is ApprovalStatus.PENDING:
                return "awaiting_approval", f"waiting for a human to approve {req.request_id}"
            return "denied_by_human", f"a human denied {req.request_id}"
