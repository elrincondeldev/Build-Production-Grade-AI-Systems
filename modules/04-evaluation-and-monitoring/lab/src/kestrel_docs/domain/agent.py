"""A tiny, deterministic support *agent* used to practise agent evaluation.

Real agents let an LLM pick tools. The evaluation problem is identical either
way: given a conversation, did the agent call the **right tool**, with the
**right arguments**, **without** calling anything dangerous, and did it
**remember** what the user already said? 📖 See lesson 4.3.

The planner below is rule-based so that the eval harness is reproducible.
Swap in an LLM planner later; the checks in ``evals/agent_checks.py`` stay
the same, and that is the point.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

PLANS = ("basic", "plus", "premium")
_LAST4 = re.compile(r"\b(?:ending(?: in)?|last four(?: digits)?(?: are)?)\s*(\d{4})\b", re.IGNORECASE)


@dataclass(frozen=True)
class ToolCall:
    tool: str
    args: dict


@dataclass
class AgentTurn:
    reply: str
    tool_calls: list[ToolCall] = field(default_factory=list)


class SupportAgent:
    """Tools: search_handbook, get_plan_fees, freeze_card (high risk), escalate_to_human."""

    def __init__(self, memory_turns: int = 5) -> None:
        # memory_turns=0 simulates an agent that "forgets" earlier turns, a very
        # common production bug (context truncated, session store misconfigured).
        self.memory_turns = memory_turns

    def _find_last4(self, texts: list[str]) -> str | None:
        for text in reversed(texts):
            match = _LAST4.search(text)
            if match:
                return match.group(1)
        return None

    def run(self, turns: list[str], role: str = "customer") -> AgentTurn:
        """Process a conversation and return the agent's action for the LAST turn."""
        message = turns[-1]
        lowered = message.lower()
        memory = turns[-1 - self.memory_turns : -1] if self.memory_turns > 0 else []

        if any(w in lowered for w in ("human", "real person", "complaint")):
            return AgentTurn(
                "Connecting you with a support specialist.",
                [ToolCall("escalate_to_human", {"reason": "customer_request"})],
            )

        if "freeze" in lowered or "block my card" in lowered:
            last4 = self._find_last4(memory + [message])
            if last4 is None:
                return AgentTurn("Which card? Please tell me the last four digits.")
            return AgentTurn(
                f"Your card ending {last4} is now frozen.",
                [ToolCall("freeze_card", {"card_last4": last4})],
            )

        plan = next((p for p in PLANS if re.search(rf"\b{p}\b", lowered)), None)
        if plan and any(w in lowered for w in ("fee", "cost", "price", "how much")):
            return AgentTurn(f"Here are the fees for {plan}.", [ToolCall("get_plan_fees", {"plan": plan})])

        return AgentTurn(
            "Let me check the handbook.",
            [ToolCall("search_handbook", {"query": message, "role": role})],
        )
