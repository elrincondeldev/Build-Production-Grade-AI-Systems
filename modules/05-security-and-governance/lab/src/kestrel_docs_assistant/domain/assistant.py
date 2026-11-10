"""The locked-down answer pipeline. Read this file top to bottom: it IS the module.

    question ─► [1 input guard] ─► [2 permission-aware retrieval] ─► [3 chunk quarantine]
             ─► [4 prompt with trust boundaries] ─► LLM ─► [5 output contract]
             ─► [6 content guards] ─► [7 citation + groundedness] ─► [8 PII redaction] ─► [9 audit] ─► answer

Every refusal has a machine-readable ``reason`` so you can count them on a
dashboard (📖 lesson 4.4) and alert when one suddenly spikes.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from ..adapters.llm import LLMClient
from ..adapters.tokens import Principal
from .access import allowed_levels
from .audit import AuditLog
from .contracts import AssistantAnswer, Citation, parse_model_output
from .documents import Chunk
from .guardrails import (
    InjectionClassifier,
    asks_for_credentials,
    check_input,
    groundedness,
    leaks_system_prompt,
    quarantine_chunks,
)
from .pii import redact
from .prompting import build_messages
from .registry import Bundle
from .retrieval import PermissionAwareBM25

REFUSAL_MESSAGES = {
    "no_relevant_context": "I can't find that in the documents available to you.",
    "model_abstained": "I can't find that in the documents available to you.",
    "input_blocked": "I can't help with that request.",
    "output_blocked": "I can't share that answer. If you need help with your account, contact Support in the app.",
    "contract_violation": "Something went wrong generating the answer. Please try again.",
    "invalid_citation": "I couldn't verify the sources for that answer, so I won't show it.",
    "ungrounded": "I couldn't verify that answer against our documents, so I won't show it.",
}


@dataclass(frozen=True)
class Layers:
    """Which defence layers are on. All on in production; toggled in the Break-it labs."""

    input_guardrails: bool = True
    scan_retrieved_chunks: bool = True
    output_guardrails: bool = True


class DocsAssistant:
    def __init__(
        self,
        *,
        index: PermissionAwareBM25,
        llm: LLMClient,
        bundle: Bundle,
        detector: InjectionClassifier,
        audit: AuditLog | None = None,
        layers: Layers = Layers(),
    ) -> None:
        self.index, self.llm, self.bundle = index, llm, bundle
        self.detector, self.audit, self.layers = detector, audit, layers

    @property
    def policy(self):  # noqa: ANN201
        return self.bundle.policy

    async def answer(self, question: str, principal: Principal, request_id: str) -> AssistantAnswer:
        trace: dict[str, object] = {"retrieved": [], "quarantined": [], "llm_called": False}
        result = await self._answer(question, principal, request_id, trace)
        if self.audit is not None:
            self.audit.append(
                "ask",
                request_id=request_id,
                actor=principal.sub,
                role=principal.role,
                question=question,  # redacted inside AuditLog.append
                policy_version=self.bundle.version,
                refused=result.refused,
                reason=result.reason,
                citations=[c.doc_id for c in result.citations],
                answer_sha256=hashlib.sha256(result.answer.encode()).hexdigest(),
                **trace,
            )
        return result

    def _refuse(self, reason: str, request_id: str) -> AssistantAnswer:
        family = reason.split(":", 1)[0]
        return AssistantAnswer(
            answer=REFUSAL_MESSAGES.get(family, REFUSAL_MESSAGES["output_blocked"]),
            confidence=0.0,
            refused=True,
            reason=reason,
            policy_version=self.bundle.version,
            request_id=request_id,
        )

    async def _answer(self, question: str, principal: Principal, request_id: str, trace: dict[str, object]) -> AssistantAnswer:
        policy = self.policy

        # 1 ── input guard (direct injection, size limits)
        if self.layers.input_guardrails:
            verdict = check_input(
                question, max_chars=policy.max_question_chars, threshold=policy.injection_threshold, detector=self.detector
            )
            if not verdict.allowed:
                trace["input_guard"] = verdict.details
                return self._refuse(verdict.reason or "input_blocked", request_id)

        # 2 ── permission-aware retrieval: filter BEFORE ranking
        allowed = allowed_levels(principal.role)
        hits = [h for h in self.index.search(question, allowed, k=policy.top_k) if h.score >= policy.min_retrieval_score]
        chunks: list[Chunk] = [h.chunk for h in hits]
        trace["retrieved"] = [h.chunk.chunk_id for h in hits]

        # 3 ── indirect injection: scan retrieved text like untrusted input
        if self.layers.scan_retrieved_chunks:
            chunks, quarantined = quarantine_chunks(chunks, threshold=policy.injection_threshold, detector=self.detector)
            trace["quarantined"] = [c.chunk_id for c, _ in quarantined]
        if not chunks:
            return self._refuse("no_relevant_context", request_id)

        # 4 ── prompt with trust boundaries; PII never leaves the building
        prompt_question = redact(question) if policy.redact_pii_in_prompts else question
        messages = build_messages(self.bundle.system_prompt, prompt_question, chunks)
        completion = await self.llm.complete(messages, temperature=0.0, max_tokens=512)
        trace["llm_called"] = True
        trace["usage"] = {"prompt_tokens": completion.prompt_tokens, "completion_tokens": completion.completion_tokens}

        # 5 ── output contract
        output = parse_model_output(completion.text)
        if output is None:
            return self._refuse("contract_violation", request_id)

        # 6 ── content guards that do not need citations: run them first
        if self.layers.output_guardrails:
            if asks_for_credentials(output.answer):
                return self._refuse("output_blocked:credential_request", request_id)
            if leaks_system_prompt(output.answer, self.bundle.system_prompt):
                return self._refuse("output_blocked:system_prompt_leak", request_id)
        if not output.citations:
            return self._refuse("model_abstained", request_id)

        # 7 ── citations must point at documents we actually gave the model, and support the answer
        by_doc: dict[str, list[Chunk]] = {}
        for chunk in chunks:
            by_doc.setdefault(chunk.doc_id, []).append(chunk)
        if any(doc_id not in by_doc for doc_id in output.citations):
            return self._refuse("invalid_citation", request_id)
        if self.layers.output_guardrails:
            cited = [c for doc_id in output.citations for c in by_doc[doc_id]]
            report = groundedness(output.answer, cited)
            trace["groundedness"] = report.score
            if report.score < policy.groundedness_threshold:
                return self._refuse("ungrounded", request_id)

        # 8 ── PII redaction on the way out
        answer_text = redact(output.answer) if policy.redact_pii_in_responses else output.answer
        citations = [Citation(doc_id=d, title=by_doc[d][0].title) for d in dict.fromkeys(output.citations)]
        return AssistantAnswer(
            answer=answer_text,
            citations=citations,
            confidence=output.confidence,
            refused=False,
            policy_version=self.bundle.version,
            request_id=request_id,
        )
