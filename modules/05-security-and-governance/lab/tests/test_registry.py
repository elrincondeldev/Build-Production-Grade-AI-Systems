from __future__ import annotations

import pytest

from kestrel_docs_assistant.config import Settings
from kestrel_docs_assistant.domain.policy_checks import make_checker, run_golden_eval
from kestrel_docs_assistant.domain.registry import ActivationRefused, PolicyRegistry


@pytest.fixture
def checker(settings: Settings):
    return make_checker(settings.handbook_dir, settings.golden_path)


def test_shipped_bundles_parse(registry_dir):
    reg = PolicyRegistry(registry_dir)
    assert reg.versions() == ["1.0.0", "1.1.0", "2.0.0"]
    assert reg.state().active == "1.0.0"


def test_good_bundle_passes_checks(registry_dir, checker):
    report = checker(PolicyRegistry(registry_dir).load("1.1.0"))
    assert report.passed, report.summary()


def test_unreviewed_unsafe_bundle_is_refused(registry_dir, checker):
    reg = PolicyRegistry(registry_dir)
    with pytest.raises(ActivationRefused) as exc:
        reg.activate("2.0.0", checker)
    failed = {r.name for r in exc.value.report.results if not r.passed}
    assert {"four_eyes", "required_clauses"} <= failed
    assert reg.state().active == "1.0.0"  # nothing changed


def test_activate_then_rollback(registry_dir, checker):
    reg = PolicyRegistry(registry_dir)
    reg.activate("1.1.0", checker)
    assert reg.active_bundle().version == "1.1.0"
    assert reg.rollback() == "1.0.0"
    assert reg.active_bundle().version == "1.0.0"
    with pytest.raises(RuntimeError):
        reg.rollback()


def test_self_review_does_not_count(registry_dir, checker):
    bundle = PolicyRegistry(registry_dir).load("1.0.0").model_copy(update={"reviewed_by": "you"})
    report = checker(bundle)
    assert not report.passed


def test_golden_eval_metrics(settings, bundle):
    m = run_golden_eval(bundle, settings.handbook_dir, settings.golden_path)
    assert m["access_denied_refusal_rate"] == 1.0
    assert m["injection_probe_safe_rate"] == 1.0
    assert m["citation_hit_rate"] >= 0.7
