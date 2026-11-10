"""JWT issuing and verification (HS256) with PyJWT.

📖 See lesson 5.3. Rules encoded here:

1. **Pin the algorithm.** ``algorithms=["HS256"]`` means a token whose header says
   ``alg: none`` (or RS256, for key-confusion tricks) is rejected outright.
2. **Require claims.** ``exp``, ``iat``, ``sub``, ``role``, ``iss``, ``aud`` must
   all be present, and ``iss``/``aud`` must match what this service expects.
3. **Small clock leeway** (30 s), not minutes.
4. **Deny unknown roles.** A valid signature is not authorization.

In production, prefer asymmetric keys (RS256/EdDSA) issued by an identity
provider, so services can verify tokens without being able to mint them.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt

from ..domain.access import ROLE_ACCESS

ALGORITHM = "HS256"
LEEWAY_SECONDS = 30


@dataclass(frozen=True)
class Principal:
    sub: str
    role: str


class TokenError(Exception):
    """Raised for any invalid token. The message is safe to log, not to return verbatim."""


def issue_token(
    sub: str,
    role: str,
    secret: str,
    *,
    issuer: str,
    audience: str,
    ttl: timedelta = timedelta(hours=1),
    now: datetime | None = None,
) -> str:
    if role not in ROLE_ACCESS:
        raise ValueError(f"unknown role {role!r}")
    now = now or datetime.now(UTC)
    claims = {"sub": sub, "role": role, "iss": issuer, "aud": audience, "iat": now, "exp": now + ttl}
    return jwt.encode(claims, secret, algorithm=ALGORITHM)


def decode_token(token: str, secret: str, *, issuer: str, audience: str) -> Principal:
    try:
        claims = jwt.decode(
            token,
            secret,
            algorithms=[ALGORITHM],  # pinned: never read the algorithm from the token
            audience=audience,
            issuer=issuer,
            leeway=LEEWAY_SECONDS,
            options={"require": ["exp", "iat", "sub", "role", "iss", "aud"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("token expired") from exc
    except jwt.InvalidTokenError as exc:  # bad signature, wrong alg, missing claim, wrong aud/iss...
        raise TokenError(f"invalid token: {type(exc).__name__}") from exc
    role = claims["role"]
    if role not in ROLE_ACCESS:
        raise TokenError("unknown role")
    return Principal(sub=str(claims["sub"]), role=str(role))
