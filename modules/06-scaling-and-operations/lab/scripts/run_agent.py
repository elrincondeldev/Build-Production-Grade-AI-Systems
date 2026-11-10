"""Run the refund-ops agent on the demo scenarios.

    uv run python scripts/run_agent.py                         # all scenarios, nobody approves
    uv run python scripts/run_agent.py --approver cli          # you are the human in the loop
    uv run python scripts/run_agent.py --approver file --approvals approvals.json
    uv run python scripts/run_agent.py --scenario large --show-trace
    KESTREL_LLM_PROVIDER=ollama uv run python scripts/run_agent.py --planner llm
"""

from __future__ import annotations

import argparse
from pathlib import Path

from kestrel_platform.adapters.llm import build_llm
from kestrel_platform.agent import AgentRunner, Limits, Task
from kestrel_platform.agent.approval import AutoApproveApprover, AutoDenyApprover, CLIApprover, FileApprover
from kestrel_platform.agent.ledger import demo_ledger
from kestrel_platform.agent.planner import LLMPlanner, RulePlanner
from kestrel_platform.agent.tools import build_registry

SCENARIOS = {
    "small": ("txn_fee_small", "€7 fee, 13 days old -> agent acts alone"),
    "large": ("txn_fee_large", "€79 fee -> above the €50 autonomy limit"),
    "old": ("txn_fee_old", "fee 101 days old -> goodwill only"),
    "blocked": ("txn_fee_blocked", "old fee, goodwill limit used -> refused"),
    "atm": ("txn_atm", "third-party ATM fee -> never refundable"),
    "fx": ("txn_fx", "FX markup 1.1% -> goodwill only"),
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", choices=["all", *SCENARIOS], default="all")
    parser.add_argument("--approver", choices=["deny", "approve", "cli", "file"], default="deny")
    parser.add_argument("--approvals", type=Path, default=Path("approvals.json"))
    parser.add_argument("--planner", choices=["rule", "llm"], default="rule")
    parser.add_argument("--max-steps", type=int, default=8)
    parser.add_argument("--show-trace", action="store_true")
    parser.add_argument("--trace-dir", type=Path, default=Path("traces"))
    args = parser.parse_args()

    approver = {
        "deny": AutoDenyApprover(),
        "approve": AutoApproveApprover(),
        "cli": CLIApprover(),
        "file": FileApprover(args.approvals),
    }[args.approver]
    ledger = demo_ledger()  # shared across scenarios, like a real database
    registry = build_registry(ledger)
    planner = LLMPlanner(build_llm(), registry) if args.planner == "llm" else RulePlanner()
    runner = AgentRunner(registry, planner, approver, Limits(max_steps=args.max_steps))

    names = list(SCENARIOS) if args.scenario == "all" else [args.scenario]
    for name in names:
        txn_id, story = SCENARIOS[name]
        result = runner.run(Task(txn_id))
        path = result.tracer.write(args.trace_dir)
        print(f"\n[{name}] {story}")
        print(f"  status : {result.status}")
        print(f"  message: {result.message}")
        for a in result.approvals:
            print(f"  approval {a['request_id']}: {a['status']} ({a['reason']})")
        print(f"  trace  : {path}")
        if args.show_trace:
            print(result.tracer.render_tree())
    if args.approver == "file" and approver.pending_path.exists():  # type: ignore[union-attr]
        print(f"\nPending approvals written to {approver.pending_path}. "  # type: ignore[union-attr]
              f"Copy an id into {args.approvals} as {{\"apr_...\": \"approve\"}} and run again.")
    print(f"\nRefunds issued this session: {ledger.refunds}")


if __name__ == "__main__":
    main()
