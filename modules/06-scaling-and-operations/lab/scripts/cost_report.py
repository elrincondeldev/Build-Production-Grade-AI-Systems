"""Generate reports/cost-report.md from cost_assumptions.toml (lesson 6.3).

    uv run python scripts/cost_report.py
    uv run python scripts/cost_report.py --assumptions my_assumptions.toml --out reports/q1.md
"""

from __future__ import annotations

import argparse
from pathlib import Path

from kestrel_platform.costs import build_report, load_assumptions


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--assumptions", type=Path, default=Path("cost_assumptions.toml"))
    p.add_argument("--out", type=Path, default=Path("reports/cost-report.md"))
    a = p.parse_args()
    report = build_report(load_assumptions(a.assumptions))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(report)
    print(report)
    print(f"\nwritten to {a.out}")


if __name__ == "__main__":
    main()
