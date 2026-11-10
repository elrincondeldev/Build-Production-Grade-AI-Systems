"""Mint a short-lived JWT for local development.

    uv run python scripts/issue_token.py --sub alice --role employee
    uv run python scripts/issue_token.py --sub eve --role customer --ttl-minutes 1

In production, tokens come from an identity provider (Okta, Entra ID, Keycloak,
Auth0, ...), never from a script with the signing secret on a laptop.
"""

from __future__ import annotations

import argparse
from datetime import timedelta

from kestrel_docs_assistant.adapters.tokens import issue_token
from kestrel_docs_assistant.config import get_settings
from kestrel_docs_assistant.domain.access import ROLE_ACCESS


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sub", required=True, help="user id, e.g. alice")
    parser.add_argument("--role", required=True, choices=sorted(ROLE_ACCESS))
    parser.add_argument("--ttl-minutes", type=float, default=None)
    args = parser.parse_args()
    s = get_settings()
    ttl = timedelta(minutes=args.ttl_minutes if args.ttl_minutes is not None else s.jwt_ttl_minutes)
    print(issue_token(args.sub, args.role, s.jwt_secret, issuer=s.jwt_issuer, audience=s.jwt_audience, ttl=ttl))


if __name__ == "__main__":
    main()
