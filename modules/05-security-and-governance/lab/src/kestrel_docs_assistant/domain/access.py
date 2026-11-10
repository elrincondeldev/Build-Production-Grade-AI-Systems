"""Role -> document access levels. The single source of truth for authorization.

📖 See lesson 5.3. Mirrors the table in datasets/handbook/README.md.
Deny by default: an unknown role gets an error, never "public" as a fallback.
"""

from __future__ import annotations

ROLE_ACCESS: dict[str, frozenset[str]] = {
    "customer": frozenset({"public"}),
    "employee": frozenset({"public", "employee"}),
    "engineer": frozenset({"public", "employee", "engineering"}),
    "hr": frozenset({"public", "employee", "hr"}),
    "finance": frozenset({"public", "employee", "finance"}),
}


class UnknownRoleError(ValueError):
    pass


def allowed_levels(role: str) -> frozenset[str]:
    try:
        return ROLE_ACCESS[role]
    except KeyError as exc:  # deny by default
        raise UnknownRoleError(f"unknown role: {role!r}") from exc
