"""How much should you trust your judge?  📖 See lesson 4.3.

Compares judge verdicts with human labels on ``evals/data/human_labels.jsonl``:

- **accuracy**: share of items where judge and human agree
- **Cohen's kappa**: agreement corrected for chance. With 90% "pass" labels a
  judge that always says "pass" gets 90% accuracy and kappa = 0.

    kappa = (p_observed − p_chance) / (1 − p_chance)

Rough reading (Landis & Koch, 1977): < 0.4 weak · 0.4–0.6 moderate ·
0.6–0.8 substantial · > 0.8 almost perfect.

Run:  uv run python -m evals.judge_calibration [--judge fake|llm]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evals.judge import FakeJudge, Judge, LLMJudge

DATA = Path(__file__).parent / "data" / "human_labels.jsonl"


def cohen_kappa(a: list[bool], b: list[bool]) -> float:
    if len(a) != len(b) or not a:
        raise ValueError("need two equally long, non-empty label lists")
    n = len(a)
    p_observed = sum(x == y for x, y in zip(a, b, strict=True)) / n
    pa, pb = sum(a) / n, sum(b) / n
    p_chance = pa * pb + (1 - pa) * (1 - pb)
    if p_chance == 1.0:
        return 1.0 if p_observed == 1.0 else 0.0
    return (p_observed - p_chance) / (1 - p_chance)


def calibrate(judge: Judge, rows: list[dict]) -> dict:
    human = [r["human_label"] == "pass" for r in rows]
    verdicts = [judge.judge(r["question"], r["expected_answer"], r["answer"]) for r in rows]
    machine = [v.passed for v in verdicts]
    confusion = {
        "both_pass": sum(h and m for h, m in zip(human, machine, strict=True)),
        "both_fail": sum(not h and not m for h, m in zip(human, machine, strict=True)),
        "judge_pass_human_fail": sum(m and not h for h, m in zip(human, machine, strict=True)),
        "judge_fail_human_pass": sum(h and not m for h, m in zip(human, machine, strict=True)),
    }
    disagreements = [
        {"id": r["id"], "human": r["human_label"], "judge": "pass" if v.passed else "fail", "reason": v.reason,
         "answer": r["answer"], "note": r.get("note", "")}
        for r, h, v in zip(rows, human, verdicts, strict=True)
        if h != v.passed
    ]
    return {
        "n": len(rows),
        "accuracy": round(sum(h == m for h, m in zip(human, machine, strict=True)) / len(rows), 3),
        "kappa": round(cohen_kappa(human, machine), 3),
        "confusion": confusion,
        "disagreements": disagreements,
    }


def load_rows(path: Path = DATA) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure judge/human agreement")
    parser.add_argument("--judge", choices=["fake", "llm"], default="fake")
    args = parser.parse_args()

    if args.judge == "llm":
        from kestrel_docs.adapters.llm import build_llm
        from kestrel_docs.config import get_settings

        judge: Judge = LLMJudge(build_llm(get_settings()))
    else:
        judge = FakeJudge()

    report = calibrate(judge, load_rows())
    c = report["confusion"]
    print(f"Judge: {args.judge}   items: {report['n']}")
    print(f"accuracy = {report['accuracy']:.2f}   Cohen's kappa = {report['kappa']:.2f}\n")
    print("                 human=pass  human=fail")
    print(f"  judge=pass        {c['both_pass']:>4}        {c['judge_pass_human_fail']:>4}")
    print(f"  judge=fail        {c['judge_fail_human_pass']:>4}        {c['both_fail']:>4}\n")
    for d in report["disagreements"]:
        print(f"✗ {d['id']}: human={d['human']} judge={d['judge']} ({d['reason']}) {d['note']}")
        print(f"    answer: {d['answer']}")


if __name__ == "__main__":
    main()
