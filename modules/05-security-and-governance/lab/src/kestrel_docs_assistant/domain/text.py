"""Tiny, dependency-free text utilities shared by retrieval, guardrails and the fake LLM.

Deliberately simple (lowercase, strip punctuation, drop stopwords, naive stemming)
so you can read every line. Production systems use proper analyzers, but the
*ideas* (lexical overlap as a cheap groundedness signal) are the same.
"""

from __future__ import annotations

import re

_TOKEN_RE = re.compile(r"[a-z0-9€%]+(?:[.,][0-9]+)*")

STOPWORDS = frozenset(
    """a an the and or but if then else of to in on at by for with from as is are was were be been being
    do does did doing have has had having i me my we our you your he she it its they them their this that
    these those what which who whom whose when where why how can could should would will shall may might
    must not no nor so than too very just about above below up down out over under again further once here
    there all any both each few more most other some such only own same into through during before after
    am also get got there's i'm don't per""".split()
)

# Words that appear in nearly every handbook page carry no signal for this corpus.
DOMAIN_STOPWORDS = frozenset({"kestrel", "pay"})


def _stem(token: str) -> str:
    """Very light suffix stripping so "opened"/"open" and "refunds"/"refund" match.

    Not linguistically correct ("charge" -> "charg"), only *consistent*, which is
    all lexical matching needs.
    """
    if len(token) > 5 and token.endswith("ing"):
        token = token[:-3]
    elif len(token) > 4 and token.endswith("ed"):
        token = token[:-2]
    elif len(token) > 3 and token.endswith("s") and not token.endswith(("ss", "us", "is")):
        token = token[:-1]
    if len(token) > 4 and token.endswith("e"):
        token = token[:-1]
    return token


def tokenize(text: str, *, keep_stopwords: bool = False) -> list[str]:
    tokens = _TOKEN_RE.findall(text.lower())
    if keep_stopwords:
        return [_stem(t) for t in tokens]
    return [_stem(t) for t in tokens if t not in STOPWORDS and t not in DOMAIN_STOPWORDS]


_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9€*\"'(])|\n+")


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(text) if s and s.strip()]


_MD_NOISE_RE = re.compile(r"(\*\*|__|`|^#+\s*|^\s*[-*]\s+|^\s*\d+\.\s+)", re.M)


def clean_markdown(text: str) -> str:
    """Remove markdown decoration so extracted sentences read like prose."""
    text = _MD_NOISE_RE.sub("", text)
    if "|" in text:  # table row -> "cell · cell · cell"
        cells = [c.strip() for c in text.strip().strip("|").split("|")]
        text = " · ".join(c for c in cells if c and not set(c) <= set("-: "))
    return text.strip()
