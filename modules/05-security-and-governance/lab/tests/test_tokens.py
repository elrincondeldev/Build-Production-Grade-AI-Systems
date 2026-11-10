"""JWT validation: the happy path and every way a token must be rejected."""

from __future__ import annotations

import base64
import json
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from kestrel_docs_assistant.adapters.tokens import TokenError, decode_token, issue_token

SECRET = "unit-secret-0123456789abcdef0123456789"
ISS, AUD = "kestrel-auth", "docs-assistant"


def _decode(token: str):
    return decode_token(token, SECRET, issuer=ISS, audience=AUD)


def test_valid_token_round_trip():
    principal = _decode(issue_token("alice", "employee", SECRET, issuer=ISS, audience=AUD))
    assert (principal.sub, principal.role) == ("alice", "employee")


def test_expired_token_rejected():
    past = datetime.now(UTC) - timedelta(hours=2)
    token = issue_token("alice", "employee", SECRET, issuer=ISS, audience=AUD, ttl=timedelta(minutes=5), now=past)
    with pytest.raises(TokenError, match="expired"):
        _decode(token)


def test_wrong_signature_rejected():
    token = issue_token("alice", "hr", "attacker-secret-0123456789abcdef012", issuer=ISS, audience=AUD)
    with pytest.raises(TokenError):
        _decode(token)


def test_alg_none_rejected():
    """The classic attack: unsigned token claiming alg=none and a privileged role."""
    def b64(obj: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(obj).encode()).rstrip(b"=").decode()

    now = int(datetime.now(UTC).timestamp())
    claims = {"sub": "mallory", "role": "hr", "iss": ISS, "aud": AUD, "iat": now, "exp": now + 3600}
    unsigned = f"{b64({'alg': 'none', 'typ': 'JWT'})}.{b64(claims)}."
    with pytest.raises(TokenError):
        _decode(unsigned)


def test_wrong_audience_rejected():
    token = issue_token("alice", "employee", SECRET, issuer=ISS, audience="billing-service")
    with pytest.raises(TokenError):
        _decode(token)


def test_missing_role_claim_rejected():
    now = datetime.now(UTC)
    token = jwt.encode({"sub": "alice", "iss": ISS, "aud": AUD, "iat": now, "exp": now + timedelta(hours=1)}, SECRET, algorithm="HS256")
    with pytest.raises(TokenError):
        _decode(token)


def test_unknown_role_rejected_even_with_valid_signature():
    now = datetime.now(UTC)
    claims = {"sub": "alice", "role": "admin", "iss": ISS, "aud": AUD, "iat": now, "exp": now + timedelta(hours=1)}
    with pytest.raises(TokenError, match="unknown role"):
        _decode(jwt.encode(claims, SECRET, algorithm="HS256"))


def test_dev_secret_refused_in_prod():
    from kestrel_docs_assistant.config import Settings

    with pytest.raises(ValueError, match="KESTREL_JWT_SECRET"):
        Settings(env="prod")
