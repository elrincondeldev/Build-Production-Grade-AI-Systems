"""Run the full offline evaluation suite and write a report. 📖 Lesson 4.3.

    uv run python -m evals.run_evals                      # active prompt version
    uv run python -m evals.run_evals --prompt-version v2  # evaluate a candidate WITHOUT activating it
    uv run python -m evals.run_evals --agent-memory 0     # simulate an agent that forgets context

Outputs:
    results/eval_report.json   aggregate metrics (input for scripts/eval_gate.py)
    results/eval_cases.jsonl   one line per case, for debugging failures
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from kestrel_docs.adapters.llm import Message
from kestrel_docs.config import LAB_DIR, Settings
from kestrel_docs.domain.agent import SupportAgent
from kestrel_docs.domain.assistant import DocsAssistant
from kestrel_docs.domain.prompt_registry import PromptRegistry, PromptVersion
from kestrel_docs.main import build_assistant

from evals.agent_checks import run_agent_cases
from evals.judge import FakeJudge, Judge
from evals.metrics import access_violation, contains_any, mean, percentile, score_golden_case

DATA_DIR = Path(__file__).parent / "data"


class PinnedPrompt:
    """Registry stand-in that always serves one version: lets you evaluate a
    candidate prompt without touching the live pointer."""

    def __init__(self, registry: PromptRegistry, version: str) -> None:
        self._prompt = registry.get(version)
        self.dir = registry.dir

    def active(self) -> PromptVersion:
        return self._prompt

    def active_version(self) -> str:
        return self._prompt.version


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


async def _run_golden(assistant: DocsAssistant, cases: list[dict], chunks_by_doc: dict, judge: Judge) -> list[dict]:
    rows = []
    for case in cases:
        answer = await assistant.ask(case["question"], case["role"])
        row = score_golden_case(case, answer, chunks_by_doc)
        row["judge_pass"] = judge.judge(case["question"], case["expected_answer"], answer.text).passed
        rows.append(row)
    return rows


async def _run_redteam(assistant: DocsAssistant, cases: list[dict], chunks_by_doc: dict) -> list[dict]:
    rows = []
    for case in cases:
        answer = await assistant.ask(case["prompt"], case["role"])
        leaked = contains_any(answer.text, case["forbidden"])
        violated = access_violation(answer, case["role"], chunks_by_doc)
        rows.append(
            {"id": case["id"], "attack": case["attack"], "answer": answer.text,
             "passed": not leaked and not violated, "leaked": leaked, "access_violation": violated}
        )
    return rows


async def _run_multi_turn(assistant: DocsAssistant, cases: list[dict]) -> list[dict]:
    rows = []
    for case in cases:
        history: list[Message] = []
        turn_results = []
        for turn in case["turns"]:
            answer = await assistant.ask(turn["question"], case["role"], history)
            ok = all(k.lower() in answer.text.lower() for k in turn["expect_keywords"])
            turn_results.append({"question": turn["question"], "answer": answer.text, "passed": ok})
            history += [Message("user", turn["question"]), Message("assistant", answer.text)]
        rows.append({"id": case["id"], "passed": all(t["passed"] for t in turn_results), "turns": turn_results})
    return rows


def run(settings: Settings, *, prompt_version: str | None = None, agent_memory: int = 5,
        judge: Judge | None = None) -> tuple[dict, list[dict]]:
    """Run every suite and return (report, case_rows)."""
    assistant = build_assistant(settings)
    assistant.cache_enabled = False  # evals must measure the system, not the cache
    if prompt_version:
        assistant.registry = PinnedPrompt(assistant.registry, prompt_version)  # type: ignore[assignment]
    chunks_by_doc = {c.doc_id: c for c in assistant.retriever.chunks}
    judge = judge or FakeJudge()

    golden = read_jsonl(settings.data_dir / "golden" / "handbook_qa.jsonl")
    redteam = read_jsonl(DATA_DIR / "redteam_pack.jsonl")
    multi = read_jsonl(DATA_DIR / "multi_turn.jsonl")
    agent_cases = read_jsonl(DATA_DIR / "agent_cases.jsonl")

    async def _all():
        return (
            await _run_golden(assistant, golden, chunks_by_doc, judge),
            await _run_redteam(assistant, redteam, chunks_by_doc),
            await _run_multi_turn(assistant, multi),
        )

    g_rows, rt_rows, mt_rows = asyncio.run(_all())
    ag_rows = run_agent_cases(agent_cases, SupportAgent(memory_turns=agent_memory))

    injection = [r["injection_resisted"] for r in g_rows if r["injection_resisted"] is not None]
    injection += [r["passed"] for r in rt_rows if r["attack"] in {"indirect_injection", "tag_spoofing"}]

    report = {
        "prompt_version": assistant.registry.active_version(),
        "model": assistant.llm.model,
        "n_golden": len(g_rows),
        "metrics": {
            "retrieval_hit_rate": mean([r["retrieval_hit"] for r in g_rows]),
            "citation_hit_rate": mean([r["citation_hit"] for r in g_rows]),
            "answer_pass_rate": mean([r["answer_pass"] for r in g_rows]),
            "faithfulness_mean": mean([r["faithfulness"] for r in g_rows]),
            "refusal_accuracy": mean([r["refusal_correct"] for r in g_rows]),
            "false_refusal_rate": mean([r["false_refusal"] for r in g_rows]),
            "judge_pass_rate": mean([r["judge_pass"] for r in g_rows]),
            "access_violations": sum(r["access_violation"] for r in g_rows + rt_rows),
            "injection_resistance": mean(injection),
            "redteam_pass_rate": mean([r["passed"] for r in rt_rows]),
            "multi_turn_pass_rate": mean([r["passed"] for r in mt_rows]),
            "agent_tool_accuracy": mean([r["tool_ok"] for r in ag_rows]),
            "agent_arg_accuracy": mean([r["args_ok"] for r in ag_rows]),
            "agent_forbidden_calls": sum(len(r["forbidden_calls"]) for r in ag_rows),
            "latency_p95_ms": percentile([r["latency_ms"] for r in g_rows], 95),
        },
    }
    by_category: dict[str, list[dict]] = {}
    for r in g_rows:
        by_category.setdefault(r["category"], []).append(r)
    report["judge_pass_by_category"] = {k: mean([r["judge_pass"] for r in v]) for k, v in sorted(by_category.items())}

    cases = (
        [{"suite": "golden", **r} for r in g_rows]
        + [{"suite": "redteam", **r} for r in rt_rows]
        + [{"suite": "multi_turn", **r} for r in mt_rows]
        + [{"suite": "agent", **r} for r in ag_rows]
    )
    return report, cases


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Module 4 offline eval suite")
    parser.add_argument("--prompt-version", default=None, help="evaluate this version instead of the active one")
    parser.add_argument("--agent-memory", type=int, default=5, help="turns of memory for the support agent")
    parser.add_argument("--judge", choices=["fake", "llm"], default="fake")
    parser.add_argument("--out", type=Path, default=LAB_DIR / "results")
    args = parser.parse_args()

    settings = Settings(otel_exporter="none")
    judge: Judge = FakeJudge()
    if args.judge == "llm":
        from kestrel_docs.adapters.llm import build_llm

        from evals.judge import LLMJudge

        judge = LLMJudge(build_llm(settings))

    report, cases = run(settings, prompt_version=args.prompt_version, agent_memory=args.agent_memory, judge=judge)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "eval_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    with (args.out / "eval_cases.jsonl").open("w", encoding="utf-8") as fh:
        for row in cases:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"prompt={report['prompt_version']}  model={report['model']}  golden cases={report['n_golden']}\n")
    for name, value in report["metrics"].items():
        print(f"  {name:<24} {value}")
    print(f"\nwrote {args.out / 'eval_report.json'} and eval_cases.jsonl")


if __name__ == "__main__":
    main()
