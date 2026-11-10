import json

import yaml

from scripts.eval_gate import evaluate_gate, main

THRESHOLDS = {
    "metrics": {
        "citation_hit_rate": {"min": 0.85},
        "access_violations": {"max": 0},
    },
    "regression": {"max_drop": 0.02},
}


def report(**metrics):
    return {"prompt_version": "v1", "model": "fake", "metrics": metrics}


def test_gate_passes_when_all_thresholds_met():
    checks = evaluate_gate(report(citation_hit_rate=0.93, access_violations=0), THRESHOLDS)
    assert all(c.passed for c in checks)


def test_gate_fails_on_quality_regression():
    checks = evaluate_gate(report(citation_hit_rate=0.0, access_violations=0), THRESHOLDS)
    assert [c.metric for c in checks if not c.passed] == ["citation_hit_rate"]


def test_gate_fails_on_any_safety_violation():
    checks = evaluate_gate(report(citation_hit_rate=0.95, access_violations=1), THRESHOLDS)
    assert not all(c.passed for c in checks)


def test_gate_fails_on_missing_metric():
    checks = evaluate_gate(report(access_violations=0), THRESHOLDS)
    assert not all(c.passed for c in checks)


def test_gate_baseline_drop():
    base = report(citation_hit_rate=0.95, access_violations=0)
    ok = evaluate_gate(report(citation_hit_rate=0.94, access_violations=0), THRESHOLDS, base)
    bad = evaluate_gate(report(citation_hit_rate=0.90, access_violations=0), THRESHOLDS, base)
    assert all(c.passed for c in ok)
    assert not all(c.passed for c in bad)


def test_main_exit_codes(tmp_path):
    th = tmp_path / "t.yaml"
    th.write_text(yaml.safe_dump(THRESHOLDS))
    good, bad = tmp_path / "good.json", tmp_path / "bad.json"
    good.write_text(json.dumps(report(citation_hit_rate=0.9, access_violations=0)))
    bad.write_text(json.dumps(report(citation_hit_rate=0.5, access_violations=0)))
    assert main(["--report", str(good), "--thresholds", str(th)]) == 0
    assert main(["--report", str(bad), "--thresholds", str(th)]) == 1
