"""Minimal structured tracing for agent runs.

The span model (trace_id, span_id, parent_id, name, attributes, status, events)
deliberately mirrors OpenTelemetry, so swapping this for the OTel SDK later
(lesson 4.4) is mechanical. Every agent run writes one JSONL file you can read,
grep, or load into a notebook.
"""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Span:
    trace_id: str
    span_id: str
    parent_id: str | None
    name: str
    start_ms: float
    end_ms: float | None = None
    status: str = "ok"  # ok | error
    attributes: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)

    @property
    def duration_ms(self) -> float | None:
        return None if self.end_ms is None else self.end_ms - self.start_ms

    def set(self, **attrs: Any) -> None:
        self.attributes.update(attrs)

    def event(self, name: str, **attrs: Any) -> None:
        self.events.append({"name": name, **attrs})


class Tracer:
    def __init__(self, trace_id: str | None = None) -> None:
        self.trace_id = trace_id or uuid.uuid4().hex[:16]
        self.spans: list[Span] = []
        self._stack: list[Span] = []

    @contextmanager
    def span(self, name: str, **attrs: Any) -> Iterator[Span]:
        parent = self._stack[-1].span_id if self._stack else None
        s = Span(self.trace_id, uuid.uuid4().hex[:8], parent, name, time.perf_counter() * 1000, attributes=dict(attrs))
        self.spans.append(s)
        self._stack.append(s)
        try:
            yield s
        except Exception as exc:
            s.status = "error"
            s.event("exception", type=type(exc).__name__, message=str(exc))
            raise
        finally:
            s.end_ms = time.perf_counter() * 1000
            self._stack.pop()

    def find(self, name: str) -> list[Span]:
        return [s for s in self.spans if s.name == name]

    def to_jsonl(self) -> str:
        return "\n".join(json.dumps({**asdict(s), "duration_ms": s.duration_ms}, default=str) for s in self.spans)

    def write(self, directory: Path) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"agent-{self.trace_id}.jsonl"
        path.write_text(self.to_jsonl() + "\n")
        return path

    def render_tree(self) -> str:
        """Human-readable tree for the terminal."""
        children: dict[str | None, list[Span]] = {}
        for s in self.spans:
            children.setdefault(s.parent_id, []).append(s)
        lines: list[str] = []

        def walk(parent: str | None, depth: int) -> None:
            for s in children.get(parent, []):
                mark = "✗" if s.status == "error" else "•"
                attrs = ", ".join(f"{k}={v}" for k, v in s.attributes.items())
                lines.append(f"{'  ' * depth}{mark} {s.name} [{(s.duration_ms or 0):.1f} ms] {attrs}")
                for e in s.events:
                    lines.append(f"{'  ' * (depth + 1)}↳ {e}")
                walk(s.span_id, depth + 1)

        walk(None, 0)
        return "\n".join(lines)
