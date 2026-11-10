"""Agent evaluation: right tool, right arguments, nothing forbidden. 📖 Lesson 4.3.

For agents, the *final text* is the least interesting thing to grade. What
matters is the **trajectory**: which tools were called, with which arguments,
in which order. Those are structured data, so you can check them exactly,
with no judge needed.
"""

from __future__ import annotations

from kestrel_docs.domain.agent import SupportAgent, ToolCall


def check_case(case: dict, calls: list[ToolCall]) -> dict:
    expected = case["expected_calls"]
    actual_names = [c.tool for c in calls]
    expected_names = [e["tool"] for e in expected]
    tool_ok = actual_names == expected_names

    args_ok = tool_ok and all(
        all(call.args.get(k) == v for k, v in exp["args"].items())  # only keys we care about
        for call, exp in zip(calls, expected, strict=True)
    )
    forbidden = [c.tool for c in calls if c.tool in case.get("forbidden_tools", [])]
    return {
        "id": case["id"],
        "expected": expected_names,
        "actual": [{"tool": c.tool, "args": c.args} for c in calls],
        "tool_ok": tool_ok,
        "args_ok": args_ok,
        "forbidden_calls": forbidden,
        "note": case.get("note", ""),
    }


def run_agent_cases(cases: list[dict], agent: SupportAgent | None = None) -> list[dict]:
    agent = agent or SupportAgent()
    return [check_case(case, agent.run(case["turns"], role=case["role"]).tool_calls) for case in cases]
