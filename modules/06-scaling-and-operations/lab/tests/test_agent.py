import json
import re
from pathlib import Path

from kestrel_platform.adapters.llm import FakeLLM
from kestrel_platform.agent import AgentRunner, Limits, Task
from kestrel_platform.agent.approval import AutoApproveApprover, AutoDenyApprover, FileApprover, GateDecision, gate_refund
from kestrel_platform.agent.ledger import demo_ledger
from kestrel_platform.agent.planner import LLMPlanner, LoopingPlanner, RulePlanner
from kestrel_platform.agent.policy import MAX_GOODWILL_REFUNDS_PER_YEAR, REFUND_WINDOW_DAYS
from kestrel_platform.agent.tools import build_registry
from kestrel_platform.config import datasets_dir


def make(approver=None, planner=None, limits=None):
    ledger = demo_ledger()
    registry = build_registry(ledger)
    return ledger, AgentRunner(registry, planner or RulePlanner(), approver or AutoDenyApprover(), limits)


def test_small_eligible_refund_runs_without_a_human() -> None:
    ledger, runner = make()
    result = runner.run(Task("txn_fee_small"))
    assert result.status == "completed"
    assert result.approvals == []
    assert ledger.refunds == [{"transaction_id": "txn_fee_small", "amount_eur": 7.0, "goodwill": False}]


def test_refund_above_50_eur_requires_approval_and_default_is_deny() -> None:
    ledger, runner = make()
    result = runner.run(Task("txn_fee_large"))
    assert result.status == "denied_by_human"
    assert ledger.refunds == []  # no money moved
    assert "autonomy limit" in result.approvals[0]["reason"]


def test_refund_above_50_eur_proceeds_when_approved() -> None:
    ledger, runner = make(AutoApproveApprover())
    assert runner.run(Task("txn_fee_large")).status == "completed"
    assert ledger.refunds[0]["amount_eur"] == 79.0


def test_out_of_window_is_goodwill_and_needs_approval() -> None:
    ledger, runner = make(AutoApproveApprover())
    result = runner.run(Task("txn_fee_old"))
    assert result.status == "completed"
    assert result.approvals and "goodwill" in result.approvals[0]["reason"]
    assert ledger.customers["cus_chloe"].goodwill_refunds_this_year == 1


def test_policy_violation_is_refused_even_if_a_human_would_approve() -> None:
    ledger, runner = make(AutoApproveApprover())
    blocked = runner.run(Task("txn_fee_blocked"))
    atm = runner.run(Task("txn_atm"))
    assert blocked.status == "refused" and "goodwill limit" in blocked.message
    assert atm.status == "refused" and "ATM" in atm.message
    assert ledger.refunds == []


def test_gate_rules() -> None:
    ok = {"eligible": True, "hard_block": False, "reasons": []}
    assert gate_refund(10, ok).decision is GateDecision.AUTO
    assert gate_refund(50.01, ok).decision is GateDecision.REQUIRE_APPROVAL
    assert gate_refund(10, {"eligible": False, "hard_block": False, "reasons": ["old"]}).decision is GateDecision.REQUIRE_APPROVAL
    assert gate_refund(10, {"eligible": False, "hard_block": True, "reasons": ["x"]}).decision is GateDecision.REFUSE


def test_agent_stops_at_max_steps() -> None:
    ledger, runner = make(planner=LoopingPlanner(), limits=Limits(max_steps=4))
    result = runner.run(Task("txn_fee_small"))
    assert result.status == "stopped_max_steps"
    assert result.steps == 4
    assert len(result.tracer.find("tool.lookup_transaction")) == 4


def test_refund_budget_per_run_is_enforced() -> None:
    ledger, runner = make(AutoApproveApprover(), limits=Limits(max_refund_total_eur=50))
    result = runner.run(Task("txn_fee_large"))
    assert result.status == "stopped_budget"
    assert ledger.refunds == []


def test_double_refund_is_impossible() -> None:
    ledger, runner = make()
    assert runner.run(Task("txn_fee_small")).status == "completed"
    second = runner.run(Task("txn_fee_small"))
    assert second.status == "refused" and "already refunded" in second.message
    assert len(ledger.refunds) == 1


def test_trace_has_a_span_per_step() -> None:
    _, runner = make()
    result = runner.run(Task("txn_fee_small"))
    names = [s.name for s in result.tracer.spans]
    assert names[0] == "agent.run"
    for expected in ("tool.lookup_transaction", "tool.check_refund_policy", "approval.gate", "tool.issue_refund"):
        assert expected in names
    root = result.tracer.spans[0]
    assert all(s.parent_id == root.span_id for s in result.tracer.spans[1:])
    lines = [json.loads(line) for line in result.tracer.to_jsonl().splitlines()]
    assert all(line["trace_id"] == root.trace_id for line in lines)


def test_file_approver_pauses_then_resumes(tmp_path: Path) -> None:
    approvals = tmp_path / "approvals.json"
    ledger, runner = make(FileApprover(approvals))
    first = runner.run(Task("txn_fee_large"))
    assert first.status == "awaiting_approval"
    request_id = first.approvals[0]["request_id"]
    assert request_id in json.loads((tmp_path / "approvals.pending.json").read_text())
    approvals.write_text(json.dumps({request_id: "approve"}))
    assert runner.run(Task("txn_fee_large")).status == "completed"


def test_llm_planner_falls_back_on_invalid_output() -> None:
    ledger = demo_ledger()
    registry = build_registry(ledger)
    planner = LLMPlanner(FakeLLM(), registry)
    result = AgentRunner(registry, planner).run(Task("txn_fee_small"))
    assert result.status == "completed"
    assert planner.fallbacks >= 3
    assert any(e["name"] == "planner_fallback" for s in result.tracer.find("planner.next_step") for e in s.events)


def test_llm_planner_uses_valid_json() -> None:
    ledger = demo_ledger()
    registry = build_registry(ledger)
    planner = LLMPlanner(FakeLLM('{"tool": "lookup_transaction", "args": {"transaction_id": "txn_fx"}}'), registry)
    result = AgentRunner(registry, planner, limits=Limits(max_steps=2)).run(Task("txn_fx"))
    assert planner.fallbacks == 0
    assert result.status == "stopped_max_steps"  # a model that repeats itself is stopped by code


def test_policy_constants_match_handbook() -> None:
    text = (datasets_dir() / "handbook" / "refund-policy.md").read_text()
    assert re.search(rf"\*\*{REFUND_WINDOW_DAYS} days\*\*", text)
    assert re.search(rf"\*\*{MAX_GOODWILL_REFUNDS_PER_YEAR} goodwill refunds per calendar year\*\*", text)
