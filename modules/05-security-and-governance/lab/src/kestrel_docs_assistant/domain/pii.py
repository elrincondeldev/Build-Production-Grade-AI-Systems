"""Regex + checksum PII detection and redaction.

📖 See lesson 5.4 "Privacy: PII and encryption".

Why checksums? A regex for "13–19 digits" also matches order numbers and
timestamps. Real card numbers satisfy the **Luhn** checksum and real IBANs
satisfy **ISO 7064 mod 97-10**, so validating them cuts false positives sharply.

This is a teaching-grade baseline. For names, addresses and many locales, use a
dedicated tool such as Microsoft Presidio (install the ``presidio`` extra), and
always measure recall on your own data: a redactor that misses 5% of emails
still leaks thousands of them at scale.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
CARD_RE = re.compile(r"(?<![\d+-])(?:\d[ -]?){12,18}\d(?![\d-])")
IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){2,7}(?: ?[A-Z0-9]{1,4})?\b")
PHONE_RE = re.compile(
    r"(?<![\w+])\+\d{1,3}(?:[ .-]?\d{2,4}){2,5}(?!\w)"  # international: +34 600 123 456
    r"|(?<!\w)\(?\d{3}\)?[ .-]\d{3}[ .-]\d{3,4}(?!\w)"  # national: 600 123 456, (555) 123-4567
)

PLACEHOLDERS = {"email": "[EMAIL]", "card": "[CARD]", "iban": "[IBAN]", "phone": "[PHONE]"}


@dataclass(frozen=True)
class PIIMatch:
    kind: str
    start: int
    end: int
    text: str


def luhn_valid(number: str) -> bool:
    digits = [int(d) for d in number if d.isdigit()]
    if not 13 <= len(digits) <= 19:
        return False
    checksum = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0


def iban_valid(iban: str) -> bool:
    compact = iban.replace(" ", "").upper()
    if not 15 <= len(compact) <= 34:
        return False
    rearranged = compact[4:] + compact[:4]
    numeric = "".join(str(int(ch, 36)) for ch in rearranged)  # A=10 ... Z=35
    return int(numeric) % 97 == 1


def find_pii(text: str) -> list[PIIMatch]:
    """Return non-overlapping matches. Higher-precision detectors claim spans first."""
    candidates: list[PIIMatch] = []
    candidates += [PIIMatch("email", m.start(), m.end(), m.group()) for m in EMAIL_RE.finditer(text)]
    candidates += [
        PIIMatch("iban", m.start(), m.end(), m.group()) for m in IBAN_RE.finditer(text) if iban_valid(m.group())
    ]
    candidates += [
        PIIMatch("card", m.start(), m.end(), m.group()) for m in CARD_RE.finditer(text) if luhn_valid(m.group())
    ]
    candidates += [
        PIIMatch("phone", m.start(), m.end(), m.group())
        for m in PHONE_RE.finditer(text)
        if 9 <= sum(ch.isdigit() for ch in m.group()) <= 15
    ]
    taken: list[PIIMatch] = []
    for match in candidates:  # order above = priority
        if all(match.end <= t.start or match.start >= t.end for t in taken):
            taken.append(match)
    return sorted(taken, key=lambda m: m.start)


def redact(text: str) -> str:
    for match in reversed(find_pii(text)):
        text = text[: match.start] + PLACEHOLDERS[match.kind] + text[match.end :]
    return text


def redact_structure(value: object) -> object:
    """Recursively redact strings inside dicts/lists (used for logs and audit records)."""
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, dict):
        return {k: redact_structure(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact_structure(v) for v in value]
    return value
