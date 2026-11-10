from pathlib import Path

import pytest

from orchestration.dag import DAG, CycleError, TaskSpec
from orchestration.pipeline import build_pipeline


def test_topological_order_respects_dependencies() -> None:
    dag = build_pipeline(Path("unused"))
    assert dag.topological_order() == ["ingest", "validate", "train", "evaluate", "register"]


def test_cycle_detection() -> None:
    dag = DAG("cyclic")
    dag.add(TaskSpec("a", lambda r: 1, ["b"]))
    dag.add(TaskSpec("b", lambda r: 1, ["a"]))
    with pytest.raises(CycleError):
        dag.topological_order()


def test_unknown_dependency() -> None:
    dag = DAG("bad")
    dag.add(TaskSpec("a", lambda r: 1, ["missing"]))
    with pytest.raises(ValueError):
        dag.topological_order()


def test_failure_skips_downstream_and_retries() -> None:
    calls = {"flaky": 0}

    def flaky(r):
        calls["flaky"] += 1
        if calls["flaky"] < 3:
            raise RuntimeError("transient")
        return "ok"

    dag = DAG("demo")
    dag.add(TaskSpec("flaky", flaky, retries=2))
    dag.add(TaskSpec("boom", lambda r: 1 / 0, ["flaky"]))
    dag.add(TaskSpec("after_boom", lambda r: "never", ["boom"]))
    dag.add(TaskSpec("independent", lambda r: "fine", []))
    runs = dag.run()
    assert runs["flaky"].status == "success" and runs["flaky"].attempts == 3
    assert runs["boom"].status == "failed" and "ZeroDivisionError" in (runs["boom"].error or "")
    assert runs["after_boom"].status == "skipped"
    assert runs["independent"].status == "success"


def test_full_pipeline_registers_a_versioned_model(tmp_path: Path) -> None:
    dag = build_pipeline(tmp_path, rows=15000, seed=3)
    runs = dag.run()
    assert all(r.status == "success" for r in runs.values()), {n: r.error for n, r in runs.items()}
    target = dag.results["register"]
    meta = (target / "metadata.json").read_text()
    assert '"sha256"' in meta and '"pr_auc"' in meta
    m = dag.results["evaluate"]
    assert m["pr_auc"] >= 3 * m["base_rate"]
    assert m["roc_auc"] > 0.65
