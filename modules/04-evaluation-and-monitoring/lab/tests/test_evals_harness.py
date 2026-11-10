"""End-to-end: the real eval suite + gate, exactly as CI runs them."""

import yaml

from evals.agent_checks import check_case
from evals.run_evals import run
from kestrel_docs.config import LAB_DIR, Settings
from kestrel_docs.domain.agent import SupportAgent, ToolCall
from scripts.eval_gate import evaluate_gate

THRESHOLDS = yaml.safe_load((LAB_DIR / "eval_thresholds.yaml").read_text())


def _gate(report):
    return [c.metric for c in evaluate_gate(report, THRESHOLDS) if not c.passed]


def test_baseline_v1_passes_the_gate(registry_dir):
    report, cases = run(Settings(prompt_registry_dir=registry_dir, otel_exporter="none"))
    assert report["prompt_version"] == "v1"
    assert _gate(report) == []
    assert report["metrics"]["access_violations"] == 0
    assert any(c["suite"] == "redteam" for c in cases)


def test_candidate_v2_is_blocked(registry_dir):
    report, _ = run(Settings(prompt_registry_dir=registry_dir, otel_exporter="none"), prompt_version="v2")
    assert "citation_hit_rate" in _gate(report)


def test_unsanitised_context_breaks_injection_resistance(registry_dir):
    settings = Settings(prompt_registry_dir=registry_dir, otel_exporter="none", sanitize_context=False)
    report, _ = run(settings)
    assert "injection_resistance" in _gate(report)


def test_agent_that_forgets_context_is_caught(registry_dir):
    report, _ = run(Settings(prompt_registry_dir=registry_dir, otel_exporter="none"), agent_memory=0)
    assert "agent_tool_accuracy" in _gate(report)


def test_check_case_flags_forbidden_and_wrong_args():
    case = {"id": "x", "expected_calls": [{"tool": "freeze_card", "args": {"card_last4": "4242"}}],
            "forbidden_tools": []}
    wrong_args = check_case(case, [ToolCall("freeze_card", {"card_last4": "1111"})])
    assert wrong_args["tool_ok"] and not wrong_args["args_ok"]

    case2 = {"id": "y", "expected_calls": [], "forbidden_tools": ["freeze_card"]}
    result = check_case(case2, SupportAgent().run(["Freeze my card ending 9999"]).tool_calls)
    assert result["forbidden_calls"] == ["freeze_card"]
