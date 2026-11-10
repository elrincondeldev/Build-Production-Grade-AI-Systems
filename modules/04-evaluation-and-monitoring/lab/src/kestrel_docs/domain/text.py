"""Tiny text utilities shared by retrieval, the fake LLM and the eval metrics.

Deliberately simple (no NLP libraries) so you can read every line. Production
systems use proper tokenizers; the *ideas* (normalise, drop stop words, compare
sets of tokens) are the same.
"""

from __future__ import annotations

import re

_WORD_RE = re.compile(r"[a-z0-9€%]+")

STOP_WORDS = frozenset(
    """
    a about above after again all also am an and any are as at be because been before being
    below between both but by can could did do does doing down during each few for from further
    had has have having he her here hers herself him himself his how i if in into is it its itself
    just me more most my myself no nor not now of off on once only or other our ours ourselves out
    over own same she should so some such than that the their theirs them themselves then there
    these they this those through to too under until up very was we were what when where which
    while who whom why will with would you your yours yourself yourselves get got
    s t don doesn isn aren
    kestrel pay
    """.split()
)
# "kestrel" and "pay" appear in almost every document, so they carry no signal
# for *which* document answers a question. Same idea as IDF in BM25 (lesson 2.5).


def _light_stem(word: str) -> str:
    """Strip a plural 's' (refunds -> refund) so simple matching is less brittle."""
    if len(word) > 4 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def tokens(text: str) -> list[str]:
    return [_light_stem(w) for w in _WORD_RE.findall(text.lower())]


def content_tokens(text: str) -> list[str]:
    return [_light_stem(w) for w in _WORD_RE.findall(text.lower()) if w not in STOP_WORDS]
