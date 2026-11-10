"""Release gate: fail the build when evals regress. 📖 See lesson 4.3 / 4.6.

    uv run python scripts/eval_gate.py                                  # thresholds only
    uv run python scripts/eval_gate.py --baseline results/baseline.json # + no-regression check

Exit code 0 = ship it, 1 = blocked. CI systems only understand exit codes,
so this tiny script is what turns "we have evals" into "evals protect users".
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

LAB_DIR = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Check:
    metric: str
    value: float | None
    rule: str
    passed: bool


def evaluate_gate(report: dict, thresholds: dict, baseline: dict | None = None) -> list[Check]:
    metrics = report["metrics"]
    max_drop = float(thresholds.get("regression", {}).get("max_drop", 0.0))
    checks: list[Check] = []
    for name, rule in thresholds["metrics"].items():
        value = metrics.get(name)
        if value is None:
            checks.append(Check(name, None, "missing from report", False))
            continue
        if "min" in rule:
            checks.append(Check(name, value, f">= {rule['min']}", value >= rule["min"]))
            if baseline is not None and baseline["metrics"].get(name) is not None:
                floor = round(baseline["metrics"][name] - max_drop, 4)
                checks.append(Check(name, value, f">= baseline-{max_drop} ({floor})", value >= floor))
        if "max" in rule:
            checks.append(Check(name, value, f"<= {rule['max']}", value <= rule["max"]))
    return checks


def render_markdown(checks: list[Check], report: dict) -> str:
    failed = [c for c in checks if not c.passed]
    header = "✅ **Eval gate passed**" if not failed else f"❌ **Eval gate failed** ({len(failed)} checks)"
    lines = [
        header,
        "",
        f"prompt `{report.get('prompt_version')}` · model `{report.get('model')}`",
        "",
        "| | metric | value | rule |",
        "|---|---|---|---|",
    ]
    for c in checks:
        lines.append(f"| {'✅' if c.passed else '❌'} | {c.metric} | {c.value} | {c.rule} |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Block releases that regress the evals")
    parser.add_argument("--report", type=Path, default=LAB_DIR / "results" / "eval_report.json")
    parser.add_argument("--thresholds", type=Path, default=LAB_DIR / "eval_thresholds.yaml")
    parser.add_argument("--baseline", type=Path, default=None)
    args = parser.parse_args(argv)

    report = json.loads(args.report.read_text(encoding="utf-8"))
    thresholds = yaml.safe_load(args.thresholds.read_text(encoding="utf-8"))
    baseline = json.loads(args.baseline.read_text(encoding="utf-8")) if args.baseline else None

    checks = evaluate_gate(report, thresholds, baseline)
    markdown = render_markdown(checks, report)
    print(markdown)
    # GitHub Actions shows this file on the run's summary page.
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(markdown + "\n")
    return 0 if all(c.passed for c in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
