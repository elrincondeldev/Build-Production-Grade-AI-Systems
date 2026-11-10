"""LLM-as-judge, pluggable. 📖 See lesson 4.3.

A judge grades an answer against a reference. Two implementations:

- ``FakeJudge``: a deterministic rule (word overlap + refusal logic). Free and
  reproducible, but blind to meaning: it cannot tell "refundable" from
  "not refundable" if the words match.
- ``LLMJudge``: asks a real model with a strict rubric and a JSON verdict.

Whichever you use, **measure its agreement with humans** before trusting it
(``judge_calibration.py``). An uncalibrated judge is just a second opinion
from an unknown source.
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from typing import Protocol

from kestrel_docs.adapters.llm import LLMClient, Message
from kestrel_docs.domain.assistant import is_refusal

from evals.metrics import token_recall


@dataclass(frozen=True)
class Verdict:
    passed: bool
    reason: str


class Judge(Protocol):
    def judge(self, question: str, expected: str, answer: str) -> Verdict: ...


def _expects_refusal(expected: str) -> bool:
    return expected.startswith("REFUSE") or expected.lower().startswith("i don't know")


class FakeJudge:
    def __init__(self, min_recall: float = 0.6) -> None:
        self.min_recall = min_recall

    def judge(self, question: str, expected: str, answer: str) -> Verdict:
        if _expects_refusal(expected):
            ok = is_refusal(answer)
            return Verdict(ok, "refused as expected" if ok else "should have refused")
        if is_refusal(answer):
            return Verdict(False, "refused an answerable question")
        recall = token_recall(expected, answer)
        return Verdict(recall >= self.min_recall, f"token recall {recall:.2f}")


JUDGE_RUBRIC = """You are a strict grader for a customer-support assistant.
Compare the ANSWER with the REFERENCE for the QUESTION.

Grade PASS only if ALL are true:
1. The answer states the same facts as the reference (numbers, yes/no, conditions). Paraphrases are fine.
2. The answer adds no claim that contradicts the reference.
3. If the reference starts with REFUSE or "I don't know", the answer must decline to answer.

Respond with JSON only: {"verdict": "pass" | "fail", "reason": "<one sentence>"}"""


class LLMJudge:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def judge(self, question: str, expected: str, answer: str) -> Verdict:
        messages = [
            Message("system", JUDGE_RUBRIC),
            Message("user", f"QUESTION: {question}\nREFERENCE: {expected}\nANSWER: {answer}"),
        ]
        completion = asyncio.run(self.llm.complete(messages, temperature=0.0, max_tokens=120))
        match = re.search(r"\{.*\}", completion.text, re.DOTALL)
        try:
            data = json.loads(match.group(0)) if match else {}
        except json.JSONDecodeError:
            data = {}
        verdict = str(data.get("verdict", "fail")).lower()
        return Verdict(verdict == "pass", str(data.get("reason", "unparseable judge output")))
