from __future__ import annotations

import pytest

from kestrel_docs_assistant.domain.pii import find_pii, iban_valid, luhn_valid, redact


@pytest.mark.parametrize(
    ("number", "valid"),
    [
        ("4111 1111 1111 1111", True),   # standard Visa test number
        ("5555-5555-5555-4444", True),   # standard Mastercard test number
        ("4111 1111 1111 1112", False),  # one digit off -> fails Luhn
        ("1234567890123", False),
    ],
)
def test_luhn(number, valid):
    assert luhn_valid(number) is valid


def test_iban_checksum():
    assert iban_valid("ES91 2100 0418 4502 0005 1332")
    assert iban_valid("GB82 WEST 1234 5698 7654 32")
    assert not iban_valid("ES91 2100 0418 4502 0005 1333")


def test_redacts_all_kinds():
    text = (
        "Contact elena.ruiz@kestrelpay.example or +34 600 123 456. "
        "Card 4111 1111 1111 1111, IBAN ES91 2100 0418 4502 0005 1332."
    )
    assert redact(text) == "Contact [EMAIL] or [PHONE]. Card [CARD], IBAN [IBAN]."


def test_does_not_redact_lookalikes():
    """Precision matters too: over-redaction destroys useful answers."""
    text = "Order 4111 1111 1111 1112 shipped on 2026-08-14; band €55,000 – €72,000; txn_0001234."
    assert redact(text) == text


def test_salary_doc_contact_is_redacted_in_hr_answers():
    text = "Contact for questions: compensation lead Elena Ruiz, elena.ruiz@kestrelpay.example, +34 600 123 456."
    kinds = sorted(m.kind for m in find_pii(text))
    assert kinds == ["email", "phone"]
    # Names need NER (e.g. Presidio): regex alone cannot find them. That gap is a lesson, not a bug.
    assert "Elena Ruiz" in redact(text)


async def test_pii_never_written_to_audit_log(client, token, settings):
    r = client.post(
        "/v1/ask",
        json={"question": "My card 4111 1111 1111 1111 was charged twice, email me at bob@example.com"},
        headers={"Authorization": f"Bearer {token('customer')}"},
    )
    assert r.status_code == 200
    log = settings.audit_log_path.read_text()
    assert "4111" not in log and "bob@example.com" not in log
    assert "[CARD]" in log and "[EMAIL]" in log
