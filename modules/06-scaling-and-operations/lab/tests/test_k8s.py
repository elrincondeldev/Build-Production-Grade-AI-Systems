import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

K8S = Path(__file__).resolve().parents[1] / "k8s"
pytestmark = pytest.mark.skipif(shutil.which("kubectl") is None, reason="kubectl not installed")


def render(overlay: str) -> list[dict]:
    out = subprocess.run(["kubectl", "kustomize", str(K8S / overlay)], check=True, capture_output=True, text=True).stdout
    return [d for d in yaml.safe_load_all(out) if d]


def by_kind(docs: list[dict], kind: str) -> dict:
    matches = [d for d in docs if d["kind"] == kind]
    assert len(matches) == 1, f"expected one {kind}, got {len(matches)}"
    return matches[0]


@pytest.mark.parametrize("overlay,namespace,replicas,min_replicas", [
    ("overlays/dev", "kestrel-dev", 1, 1),
    ("overlays/prod", "kestrel-prod", 3, 3),
])
def test_overlays(overlay: str, namespace: str, replicas: int, min_replicas: int) -> None:
    docs = render(overlay)
    assert all(d["metadata"].get("namespace") == namespace for d in docs)
    dep = by_kind(docs, "Deployment")
    assert dep["spec"]["replicas"] == replicas
    container = dep["spec"]["template"]["spec"]["containers"][0]
    for probe in ("startupProbe", "readinessProbe", "livenessProbe"):
        assert probe in container
    assert container["readinessProbe"]["httpGet"]["path"] == "/ready"
    assert container["resources"]["requests"]["cpu"]
    assert by_kind(docs, "HorizontalPodAutoscaler")["spec"]["minReplicas"] == min_replicas
    # ConfigMap name carries a content hash, and the Deployment references the hashed name.
    cm = by_kind(docs, "ConfigMap")["metadata"]["name"]
    assert cm.startswith("kestrel-platform-config-")
    assert any(ref.get("configMapRef", {}).get("name") == cm for ref in container["envFrom"])


def test_secrets_only_generated_in_dev() -> None:
    assert any(d["kind"] == "Secret" for d in render("overlays/dev"))
    assert not any(d["kind"] == "Secret" for d in render("overlays/prod"))


def test_rollout_matches_deployment_policy() -> None:
    docs = render("rollout")
    rollout = by_kind(docs, "Rollout")
    weights = [s["setWeight"] for s in rollout["spec"]["strategy"]["canary"]["steps"] if "setWeight" in s]
    assert weights == [5, 25, 100]
    analysis = by_kind(docs, "AnalysisTemplate")
    conditions = {m["name"]: m["successCondition"] for m in analysis["spec"]["metrics"]}
    assert "0.01" in conditions["error-rate"]
    assert "1.20" in conditions["p95-latency-ratio"]
    hpa = by_kind(docs, "HorizontalPodAutoscaler")
    assert hpa["spec"]["scaleTargetRef"]["kind"] == "Rollout"
