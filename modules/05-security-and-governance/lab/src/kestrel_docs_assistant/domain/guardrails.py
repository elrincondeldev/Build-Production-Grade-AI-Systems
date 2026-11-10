"""Input and output guardrails.

📖 See lessons 5.2 (prompt injection) and 5.5 (guardrails and groundedness).

No single check here is reliable on its own: heuristics miss paraphrases,
classifiers have false negatives, models can be talked into anything. The point
is **defence in depth**: several cheap, independent layers, so an attack has to
beat all of them at once. The lab's tests prove that each layer alone blocks
the partner-faq attack.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Protocol

from .documents import Chunk
from .text import split_sentences, tokenize


# --------------------------------------------------------------------------- injection
@dataclass(frozen=True)
class InjectionVerdict:
    score: float  # 0..1, estimated probability-ish that the text is an injection
    matches: tuple[str, ...] = ()


class InjectionClassifier(Protocol):
    """Pluggable: swap the heuristic for a model (e.g. a fine-tuned classifier
    or Llama Guard / Prompt Guard style models) without touching the pipeline."""

    def score(self, text: str) -> InjectionVerdict: ...


_INJECTION_PATTERNS: list[tuple[str, float, re.Pattern[str]]] = [
    (
        "override_instructions",
        0.9,
        re.compile(
            r"\b(ignore|disregard|forget|override)\b[^.\n]{0,30}\b(previous|prior|above|earlier|all|your)\b"
            r"[^.\n]{0,20}\b(instructions?|rules|prompts?|guidelines)\b",
            re.I,
        ),
    ),
    (
        "prompt_extraction",
        0.8,
        re.compile(
            r"\b(reveal|show|print|repeat|output|tell me)\b[^.\n]{0,40}\b(system prompt|your (instructions|rules|prompt)|initial prompt)\b",
            re.I,
        ),
    ),
    ("jailbreak_persona", 0.7, re.compile(r"\b(developer mode|do anything now|DAN mode|jailbreak)\b", re.I)),
    ("fake_system_message", 0.6, re.compile(r"(\bsystem (note|message|override)\b|<\s*/?\s*system\s*>|\[system\])", re.I)),
    ("addresses_the_ai", 0.5, re.compile(r"\b(to|attention|note for)\b[^.\n]{0,10}\b(ai|llm|assistant)s?\b", re.I)),
    ("role_play", 0.4, re.compile(r"\b(you are now|pretend (to be|you are)|act as|roleplay as)\b", re.I)),
    ("encoded_payload", 0.3, re.compile(r"[A-Za-z0-9+/]{80,}={0,2}")),
]


class HeuristicInjectionDetector:
    """Weighted pattern matching combined with a noisy-OR: 1 - Π(1 - w)."""

    def score(self, text: str) -> InjectionVerdict:
        hits = [(name, w) for name, w, pattern in _INJECTION_PATTERNS if pattern.search(text)]
        score = 1 - math.prod(1 - w for _, w in hits) if hits else 0.0
        return InjectionVerdict(round(score, 3), tuple(name for name, _ in hits))


@dataclass(frozen=True)
class GuardVerdict:
    allowed: bool
    reason: str | None = None
    details: dict[str, object] = field(default_factory=dict)


def check_input(question: str, *, max_chars: int, threshold: float, detector: InjectionClassifier) -> GuardVerdict:
    if not question.strip():
        return GuardVerdict(False, "input_blocked:empty")
    if len(question) > max_chars:  # OWASP LLM10: unbounded consumption
        return GuardVerdict(False, "input_blocked:too_long", {"chars": len(question), "max": max_chars})
    verdict = detector.score(question)
    if verdict.score >= threshold:
        return GuardVerdict(False, "input_blocked:prompt_injection", {"score": verdict.score, "matches": verdict.matches})
    return GuardVerdict(True, details={"injection_score": verdict.score})


def quarantine_chunks(
    chunks: list[Chunk], *, threshold: float, detector: InjectionClassifier
) -> tuple[list[Chunk], list[tuple[Chunk, InjectionVerdict]]]:
    """Indirect injection defence: retrieved text is scanned like user input."""
    kept, quarantined = [], []
    for chunk in chunks:
        verdict = detector.score(chunk.text)
        if verdict.score >= threshold:
            quarantined.append((chunk, verdict))
        else:
            kept.append(chunk)
    return kept, quarantined


# --------------------------------------------------------------------------- output
_SECRET_TERMS = r"(full card number|card number|cvv|cvc|security code|pin\b|app pin|password|one-time pass(code|word)|otp)"
_CREDENTIAL_REQUEST_RE = re.compile(
    rf"\b(confirm|provide|send|share|enter|give|type|reply with|tell (me|us))\b[^.\n]{{0,60}}\b{_SECRET_TERMS}", re.I
)
_NEGATION_RE = re.compile(r"\b(never|not|don't|do not|won't|will not|no one|nobody)\b", re.I)


def asks_for_credentials(answer: str) -> bool:
    """True if any sentence *asks the user* for secrets (and is not a 'we never ask' warning)."""
    for sentence in split_sentences(answer):
        if _CREDENTIAL_REQUEST_RE.search(sentence) and not _NEGATION_RE.search(sentence):
            return True
    return False


def leaks_system_prompt(answer: str, system_prompt: str, *, n: int = 8) -> bool:
    """OWASP LLM07: flag answers that reproduce any n-word run of the system prompt."""
    words = tokenize(system_prompt, keep_stopwords=True)
    grams = {" ".join(words[i : i + n]) for i in range(len(words) - n + 1)}
    answer_words = tokenize(answer, keep_stopwords=True)
    return any(" ".join(answer_words[i : i + n]) in grams for i in range(len(answer_words) - n + 1))


@dataclass(frozen=True)
class GroundednessReport:
    score: float  # share of checkable sentences supported by the cited chunks
    unsupported: tuple[str, ...]


def groundedness(answer: str, cited_chunks: list[Chunk], *, min_overlap: float = 0.6) -> GroundednessReport:
    """Lexical groundedness: is each answer sentence supported by the cited text?

    A sentence is 'supported' when >= ``min_overlap`` of its content words appear
    in the cited chunks. Cheap, transparent and surprisingly useful as a first
    gate. Its blind spots (paraphrase, negation, numbers in the wrong place) are
    why production systems add an NLI model or an LLM judge on top (📖 lesson 4.3).
    """
    if not cited_chunks:
        return GroundednessReport(0.0, (answer,))
    support = set()
    for chunk in cited_chunks:
        support.update(tokenize(chunk.title + " " + chunk.text))
    checkable, unsupported = 0, []
    for sentence in split_sentences(answer):
        words = tokenize(sentence)
        if len(words) < 2:
            continue
        checkable += 1
        if sum(w in support for w in words) / len(words) < min_overlap:
            unsupported.append(sentence)
    if checkable == 0:
        return GroundednessReport(1.0, ())
    return GroundednessReport(round(1 - len(unsupported) / checkable, 3), tuple(unsupported))
