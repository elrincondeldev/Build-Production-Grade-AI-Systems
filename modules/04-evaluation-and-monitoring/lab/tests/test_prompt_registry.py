import pytest

from kestrel_docs.domain.prompt_registry import PromptRegistry


def test_active_version_and_render(registry_dir):
    reg = PromptRegistry(registry_dir, "docs_assistant")
    assert reg.versions() == ["v1", "v2"]
    prompt = reg.active()
    assert prompt.version == "v1"
    assert "Question: why?" in prompt.render_user(context="<doc/>", question="why?")


def test_activate_then_rollback(registry_dir):
    reg = PromptRegistry(registry_dir, "docs_assistant")
    reg.activate("v2", by="lena", reason="shorter answers")
    assert reg.active_version() == "v2"
    restored = reg.rollback(by="you", reason="eval gate failed")
    assert restored == "v1"
    assert reg.active_version() == "v1"
    reasons = [h["reason"] for h in reg.history()]
    assert reasons[-1].startswith("rollback:")  # the audit trail keeps every change


def test_unknown_version_is_rejected(registry_dir):
    reg = PromptRegistry(registry_dir, "docs_assistant")
    with pytest.raises(KeyError):
        reg.activate("v99", by="x", reason="typo")
    assert reg.active_version() == "v1"


def test_rollback_with_single_version_fails(registry_dir):
    with pytest.raises(RuntimeError):
        PromptRegistry(registry_dir, "docs_assistant").rollback(by="x", reason="nothing to undo")
