"""Permission-aware retrieval: forbidden documents never reach the prompt."""

from __future__ import annotations

import pytest

from kestrel_docs_assistant.domain.access import ROLE_ACCESS, UnknownRoleError, allowed_levels
from kestrel_docs_assistant.domain.documents import chunk_document, load_corpus
from kestrel_docs_assistant.domain.retrieval import PermissionAwareBM25

from .conftest import ask, build_assistant


def test_unknown_role_denied():
    with pytest.raises(UnknownRoleError):
        allowed_levels("admin")


@pytest.mark.parametrize("role", sorted(ROLE_ACCESS))
def test_search_only_returns_allowed_levels(settings, role):
    chunks = [c for d in load_corpus(settings.handbook_dir) for c in chunk_document(d)]
    index = PermissionAwareBM25(chunks)
    allowed = allowed_levels(role)
    for query in ["salary band staff engineer", "LLM API budget", "deploy freeze canary", "refund fee", "parental leave"]:
        for hit in index.search(query, allowed, k=10):
            assert hit.chunk.access in allowed, f"{role} got {hit.chunk.chunk_id} ({hit.chunk.access})"


async def test_customer_salary_question_is_refused_and_hr_text_never_reaches_prompt(settings, bundle):
    assistant, llm = build_assistant(settings, bundle)
    result = await ask(assistant, "What is the salary band for a Staff Engineer?", "customer")
    assert result.refused
    assert "72,000" not in result.answer and "95,000" not in result.answer
    for prompt in llm.prompts:
        assert "salary-bands" not in prompt
        assert "€72,000" not in prompt


async def test_hr_can_read_salary_bands(settings, bundle):
    assistant, _ = build_assistant(settings, bundle)
    result = await ask(assistant, "What is the salary band for a Senior Engineer?", "hr")
    assert not result.refused
    assert [c.doc_id for c in result.citations] == ["salary-bands"]
    assert "55,000" in result.answer


async def test_employee_cannot_see_finance(settings, bundle):
    assistant, llm = build_assistant(settings, bundle)
    result = await ask(assistant, "What is the Q4 GPU budget?", "employee")
    assert result.refused
    assert all("q4-budget-plan" not in p for p in llm.prompts)


async def test_idf_statistics_do_not_depend_on_forbidden_documents(settings):
    """Side-channel check: a customer's scores must be identical whether or not HR docs exist."""
    docs = load_corpus(settings.handbook_dir)
    all_chunks = [c for d in docs for c in chunk_document(d)]
    public_only = [c for c in all_chunks if c.access == "public"]
    allowed = allowed_levels("customer")
    with_hr = PermissionAwareBM25(all_chunks).search("salary engineer band", allowed, k=10)
    without_hr = PermissionAwareBM25(public_only).search("salary engineer band", allowed, k=10)
    assert [(h.chunk.chunk_id, h.score) for h in with_hr] == [(h.chunk.chunk_id, h.score) for h in without_hr]
