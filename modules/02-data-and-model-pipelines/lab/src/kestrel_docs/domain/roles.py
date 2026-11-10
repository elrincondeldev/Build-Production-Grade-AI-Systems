"""Which access levels each role may read (mirrors datasets/handbook/README.md).

⚠️ In this module the role is just a request field, i.e. the caller can claim to
be anyone. That is fine for learning retrieval filters and NOT fine in
production. Module 5 (lesson 5.3) derives the role from a verified JWT instead.
"""

from typing import Literal

Role = Literal["customer", "employee", "engineer", "hr", "finance"]

ROLE_ACCESS: dict[str, list[str]] = {
    "customer": ["public"],
    "employee": ["public", "employee"],
    "engineer": ["public", "employee", "engineering"],
    "hr": ["public", "employee", "hr"],
    "finance": ["public", "employee", "finance"],
}


def allowed_access(role: str) -> list[str]:
    try:
        return ROLE_ACCESS[role]
    except KeyError:
        raise ValueError(f"unknown role {role!r}") from None  # fail closed
