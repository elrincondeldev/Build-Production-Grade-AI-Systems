"""Planners decide WHAT to do next; workers (the runner + tools) DO it.

- RulePlanner: deterministic. For a well-defined workflow like a refund, this
  is usually the *right* production choice (see "when not to use agents", lesson 6.6).
- LLMPlanner: asks an LLM for the next step as JSON, validates it against the
  tool registry, and falls back to the RulePlanner if the output is invalid.
  The LLM proposes; code disposes.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any, Protocol

from kestrel_platform.adapters.llm import LLMClient, Message
from kestrel_platform.agent.tools import ToolRegistry


@dataclass(frozen=True)
class Step:
    tool: str
    args: dict[str, Any]


@dataclass(frozen=True)
class Finish:
    status: str  # completed | refused
    message: str


@dataclass
class AgentState:
    task: dict[str, Any]
    observations: dict[str, Any] = field(default_factory=dict)  # tool name -> last result
    history: list[Step] = field(default_factory=list)


class Planner(Protocol):
    name: str

    def next_step(self, state: AgentState) -> Step | Finish: ...


class RulePlanner:
    name = "rule"

    def next_step(self, state: AgentState) -> Step | Finish:
        txn_id = state.task["transaction_id"]
        obs = state.observations
        if "lookup_transaction" not in obs:
            return Step("lookup_transaction", {"transaction_id": txn_id})
        if "check_refund_policy" not in obs:
            return Step("check_refund_policy", {"transaction_id": txn_id})
        policy = obs["check_refund_policy"]
        if policy["hard_block"]:
            return Finish("refused", "; ".join(policy["reasons"]))
        if "issue_refund" not in obs:
            amount = float(obs["lookup_transaction"]["amount_eur"])
            return Step("issue_refund", {"transaction_id": txn_id, "amount_eur": amount, "goodwill": not policy["eligible"]})
        return Finish("completed", f"refunded €{obs['issue_refund']['amount_eur']:.2f}")


class LoopingPlanner:
    """A deliberately broken planner that never finishes. Used to prove max_steps works."""

    name = "looping"

    def next_step(self, state: AgentState) -> Step | Finish:
        return Step("lookup_transaction", {"transaction_id": state.task["transaction_id"]})


class LLMPlanner:
    name = "llm"

    def __init__(self, llm: LLMClient, registry: ToolRegistry, fallback: Planner | None = None) -> None:
        self.llm, self.registry = llm, registry
        self.fallback = fallback or RulePlanner()
        self.fallbacks = 0
        self.last_used_fallback = False

    def _prompt(self, state: AgentState) -> list[Message]:
        system = (
            "You are a refund operations planner. Choose exactly ONE next action.\n"
            f"Tools:\n{self.registry.describe()}\n"
            'Reply with JSON only: {"tool": "<name>", "args": {...}} or {"finish": "completed|refused", "message": "..."}'
        )
        user = json.dumps({"task": state.task, "observations": state.observations}, default=str)
        return [Message("system", system), Message("user", user)]

    def next_step(self, state: AgentState) -> Step | Finish:
        completion = asyncio.run(self.llm.complete(self._prompt(state), temperature=0.0, max_tokens=200))
        try:
            data = json.loads(completion.text)
            if "finish" in data:
                decision: Step | Finish = Finish(str(data["finish"]), str(data.get("message", "")))
            else:
                self.registry.validate(data["tool"], data["args"])
                decision = Step(data["tool"], data["args"])
            self.last_used_fallback = False
            return decision
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            # Invalid output is normal for LLMs; never execute it, never crash.
            self.fallbacks += 1
            self.last_used_fallback = True
            return self.fallback.next_step(state)
