"""Prompt & policy registry: versioned, reviewed, checked, released, reversible.

📖 See lesson 5.7. A *bundle* is the unit of release: system prompt + guardrail
policy, versioned together, because a prompt change and a threshold change can
interact. Bundles are immutable files; activating one is a separate, audited
action that only succeeds if the offline checks pass.

Layout::

    registry/
      bundles/1.0.0.json      immutable once written
      bundles/1.1.0.json
      state.json              {"active": "1.1.0", "history": ["1.0.0", "1.1.0"]}
"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class Policy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    top_k: int = Field(4, ge=1, le=10)
    min_retrieval_score: float = Field(1.0, ge=0)
    injection_threshold: float = Field(0.7, gt=0, le=1)
    groundedness_threshold: float = Field(0.6, ge=0, le=1)
    redact_pii_in_prompts: bool = True
    redact_pii_in_responses: bool = True
    max_question_chars: int = Field(1000, ge=50, le=20_000)


class Bundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str
    description: str
    created_by: str
    reviewed_by: str | None = None
    created_at: str
    system_prompt: str = Field(min_length=50)
    policy: Policy


class RegistryState(BaseModel):
    active: str | None = None
    history: list[str] = Field(default_factory=list)


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class CheckReport:
    version: str
    results: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return bool(self.results) and all(r.passed for r in self.results)

    def summary(self) -> str:
        lines = [f"Checks for bundle {self.version}:"]
        lines += [f"  {'PASS' if r.passed else 'FAIL'}  {r.name:<24} {r.detail}" for r in self.results]
        lines.append("RESULT: " + ("all checks passed" if self.passed else "BLOCKED"))
        return "\n".join(lines)


class ActivationRefused(RuntimeError):
    def __init__(self, report: CheckReport) -> None:
        super().__init__(report.summary())
        self.report = report


Checker = Callable[[Bundle], CheckReport]


class PolicyRegistry:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.bundles_dir = root / "bundles"
        self.state_path = root / "state.json"

    # ---- read
    def versions(self) -> list[str]:
        return sorted((p.stem for p in self.bundles_dir.glob("*.json")), key=_version_key)

    def load(self, version: str) -> Bundle:
        path = self.bundles_dir / f"{version}.json"
        if not path.exists():
            raise FileNotFoundError(f"no bundle {version!r} in {self.bundles_dir}")
        return Bundle.model_validate_json(path.read_text(encoding="utf-8"))

    def state(self) -> RegistryState:
        if not self.state_path.exists():
            return RegistryState()
        return RegistryState.model_validate_json(self.state_path.read_text(encoding="utf-8"))

    def active_bundle(self) -> Bundle:
        state = self.state()
        if not state.active:
            raise RuntimeError("no active bundle: run `registry_cli.py activate <version>`")
        return self.load(state.active)

    # ---- write
    def _write_state(self, state: RegistryState) -> None:
        # atomic write: a crash mid-write must never leave a half-written state file
        fd, tmp = tempfile.mkstemp(dir=self.root, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(state.model_dump_json(indent=2) + "\n")
        os.replace(tmp, self.state_path)

    def activate(self, version: str, checker: Checker) -> CheckReport:
        bundle = self.load(version)
        report = checker(bundle)
        if not report.passed:
            raise ActivationRefused(report)
        state = self.state()
        state.active = version
        state.history.append(version)
        self._write_state(state)
        return report

    def rollback(self) -> str:
        """Re-activate the previously active bundle. No checks: it already passed them
        when it was released, and rollback must be fast and boring."""
        state = self.state()
        if len(state.history) < 2:
            raise RuntimeError("nothing to roll back to")
        state.history.pop()
        state.active = state.history[-1]
        self._write_state(state)
        return state.active


def _version_key(version: str) -> tuple[int, ...]:
    return tuple(int(p) if p.isdigit() else 0 for p in version.replace("-", ".").split("."))
