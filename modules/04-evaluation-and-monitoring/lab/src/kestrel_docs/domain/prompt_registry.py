"""A minimal file-based prompt registry. 📖 See lesson 4.6.

Layout::

    prompts/registry/<prompt_name>/
        v1.yaml        # immutable once released
        v2.yaml
        active.yaml    # pointer to the live version + an audit history

Why bother?  A prompt is production code that changes model behaviour. If it
lives as a string literal inside the service, you cannot answer "which prompt
produced this answer?", cannot evaluate a candidate before it ships, and cannot
roll back without a redeploy. Module 5 (lesson 5.7) adds review and approvals
on top of this.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import yaml


@dataclass(frozen=True)
class PromptVersion:
    name: str
    version: str
    system: str
    user_template: str
    author: str = "unknown"
    change_note: str = ""

    def render_user(self, *, context: str, question: str) -> str:
        return self.user_template.format(context=context, question=question)


class PromptRegistry:
    def __init__(self, root: Path, name: str) -> None:
        self.dir = Path(root) / name
        self.name = name
        if not self.dir.is_dir():
            raise FileNotFoundError(f"No prompt registry folder at {self.dir}")

    # ------------------------------------------------------------------ reads
    def versions(self) -> list[str]:
        found = [p.stem for p in self.dir.glob("v*.yaml")]
        return sorted(found, key=lambda v: int(v[1:]))

    def get(self, version: str) -> PromptVersion:
        path = self.dir / f"{version}.yaml"
        if not path.exists():
            raise KeyError(f"Prompt {self.name}:{version} does not exist")
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return PromptVersion(
            name=self.name,
            version=version,
            system=data["system"],
            user_template=data["user_template"],
            author=data.get("author", "unknown"),
            change_note=data.get("change_note", ""),
        )

    def _pointer(self) -> dict:
        return yaml.safe_load((self.dir / "active.yaml").read_text(encoding="utf-8"))

    def active_version(self) -> str:
        return str(self._pointer()["active"])

    def active(self) -> PromptVersion:
        return self.get(self.active_version())

    def history(self) -> list[dict]:
        return list(self._pointer().get("history", []))

    # ----------------------------------------------------------------- writes
    def _write_pointer(self, pointer: dict) -> None:
        # Write to a temp file then rename: readers never see a half-written file.
        fd, tmp = tempfile.mkstemp(dir=self.dir, suffix=".yaml")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            yaml.safe_dump(pointer, fh, sort_keys=False)
        os.replace(tmp, self.dir / "active.yaml")

    def activate(self, version: str, *, by: str, reason: str) -> None:
        self.get(version)  # raises if the version does not exist
        pointer = self._pointer()
        pointer["active"] = version
        pointer.setdefault("history", []).append(
            {
                "version": version,
                "activated_at": datetime.now(UTC).isoformat(timespec="seconds"),
                "by": by,
                "reason": reason,
            }
        )
        self._write_pointer(pointer)

    def rollback(self, *, by: str, reason: str) -> str:
        """Re-activate the version that was live before the current one."""
        current = self.active_version()
        for entry in reversed(self.history()):
            if entry["version"] != current:
                self.activate(entry["version"], by=by, reason=f"rollback: {reason}")
                return entry["version"]
        raise RuntimeError("Nothing to roll back to: only one version was ever active")
