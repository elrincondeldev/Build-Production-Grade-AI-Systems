"""Structured-output contracts.

📖 See lesson 5.5. The model must return JSON matching ``ModelOutput``. Anything
else (prose, extra keys, a confidence of 7) is a *contract violation* and the
request fails closed with a refusal. Downstream code never parses free text.
"""

from __future__ import annotations

import json
import re

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class ModelOutput(BaseModel):
    """What we ask the LLM to produce."""

    model_config = ConfigDict(extra="forbid")

    answer: str = Field(min_length=1, max_length=2000)
    citations: list[str] = Field(default_factory=list, max_length=8)
    confidence: float = Field(ge=0.0, le=1.0)


class Citation(BaseModel):
    doc_id: str
    title: str


class AssistantAnswer(BaseModel):
    """What the API returns. Citations are the user-facing *explanation* (📖 lesson 5.6)."""

    answer: str
    citations: list[Citation] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    refused: bool
    reason: str | None = None
    policy_version: str
    request_id: str


_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.S)


def parse_model_output(text: str) -> ModelOutput | None:
    """Return a validated ModelOutput, or None if the model broke the contract."""
    match = _JSON_OBJECT_RE.search(text)  # tolerate ```json fences around the object
    if not match:
        return None
    try:
        return ModelOutput.model_validate(json.loads(match.group()))
    except (json.JSONDecodeError, ValidationError):
        return None
