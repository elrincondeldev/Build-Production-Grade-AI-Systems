"""Check the course's stable IDs.

    python3 tools/check_ids.py

Every module, lesson, lab, lab step, predict-first question, check-yourself question,
explain-it-back prompt and quiz question carries an ID as an HTML comment such as
`<!-- id: c-2-5-3 -->` (invisible on GitHub). Learner progress on the Real Env platform is
keyed by these IDs, so an ID is a name, not a position: it never changes, is never reused,
and stays with its item if the item moves. `tools/issued-ids.txt` records every ID ever
issued, so a removed ID stays retired.

The check fails when an item has no ID or one of the wrong kind, an ID is malformed,
duplicated or unregistered, an issued ID disappears without being marked retired, or an
item is written in a format this check (and the platform) can't read.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LEDGER = REPO_ROOT / "tools" / "issued-ids.txt"
ID = re.compile(r"<!-- id: ([^ ]+) -->")
N = r"(?:0|[1-9]\d*)"
GRAMMAR = re.compile(
    rf"^(?:m-{N}|l-{N}-{N}|[pc]-{N}-{N}-{N}|e-{N}-{N}|q-{N}-{N}|lab-{N}(?:-step-{N})?)$"
)


def numbered_lines(text: str) -> list[tuple[int, str, bool]]:
    """(line number, line, inside a code fence) for every line."""
    rows, in_code = [], False
    for number, line in enumerate(text.split("\n"), start=1):
        fence = re.match(r"^\s*(```|~~~)", line) is not None
        rows.append((number, line, in_code or fence))
        if fence:
            in_code = not in_code
    return rows


def sections(rows: list[tuple[int, str, bool]]) -> dict[str, list[tuple[int, str, bool]]]:
    """Rows under each '## ' heading (outside code), keyed by the heading text."""
    result: dict[str, list[tuple[int, str, bool]]] = {}
    current = None
    for row in rows:
        number, line, code = row
        if not code and line.startswith("## "):
            current = line[3:].strip()
            result[current] = []
        elif current is not None:
            result[current].append(row)
    return result


def section(rows, heading: str):
    return next((body for name, body in sections(rows).items() if name.startswith(heading)), [])


class Checker:
    def __init__(self) -> None:
        self.problems: list[str] = []
        self.found: dict[str, str] = {}

    def problem(self, where: str, message: str) -> None:
        self.problems.append(f"✘ {where}: {message}")

    def expect(self, where: str, line: str, pattern: str, what: str) -> None:
        """`line` must carry exactly one ID, of the kind `pattern` (a regex) describes."""
        ids = ID.findall(line)
        if not ids:
            self.problem(where, f"{what} has no ID")
        elif len(ids) > 1:
            self.problem(where, f"{what} has {len(ids)} IDs")
        elif not GRAMMAR.match(ids[0]):
            self.problem(where, f"malformed ID '{ids[0]}'")
        elif not re.fullmatch(pattern, ids[0]):
            shape = pattern.replace(N, "N")
            self.problem(where, f"ID '{ids[0]}' doesn't fit a {what} here (expected {shape})")

    def file(self, path: Path) -> None:
        relative = path.relative_to(REPO_ROOT)
        rows = numbered_lines(path.read_text(encoding="utf-8"))
        module = int(path.relative_to(REPO_ROOT / "modules").parts[0][:2])
        at = lambda number: f"{relative}:{number}"  # noqa: E731
        line_after = lambda index: rows[index + 1][1] if index + 1 < len(rows) else ""  # noqa: E731

        for number, line, code in rows:
            for ident in ID.findall(line):
                if code:
                    continue  # an example in a code block, not an annotation
                if ident in self.found:
                    self.problem(at(number), f"duplicate ID '{ident}' (also at {self.found[ident]})")
                else:
                    self.found[ident] = at(number)

        lesson = re.match(r"(\d\d)-", path.name)
        if path.name == "README.md" and path.parent.name == "lab":
            self.expect(at(2), line_after(0), rf"lab-{module}", "lab title")
            for index, (number, line, code) in enumerate(rows):
                if code:
                    continue
                if re.match(r"^#{2,3} Step \d+", line):
                    m = re.match(r"^### Step (\d+) · .+$", line)
                    if not m:
                        self.problem(at(number), f"step heading must read '### Step N · Title': {line}")
                    else:
                        self.expect(at(number + 1), line_after(index), rf"lab-{module}-step-{N}", "lab step")
        elif path.name == "README.md":
            self.expect(at(2), line_after(0), rf"m-{module}", "module title")
        elif path.name == "quiz.md":
            for number, line, code in rows:
                if code:
                    continue
                if re.match(r"^### \d+\.|^<details><summary><b>\d", line):
                    self.problem(at(number), "quiz question must read '**N.** …'")
                if re.match(r"^\*\*\d+\.\*\* ", line):
                    self.expect(at(number), line, rf"q-{module}-{N}", "quiz question")
        elif lesson:
            base = f"{module}-{int(lesson.group(1))}"
            self.expect(at(2), line_after(0), rf"l-{base}", "lesson title")
            for number, line, code in section(rows, "🤔 Predict first"):
                if code or not line.strip():
                    continue
                if re.match(r"^\d+\. ", line):
                    self.expect(at(number), line, rf"p-{base}-{N}", "predict question")
                elif re.match(r"^\s*(\d+\)|[-*] |\d+\. )", line):
                    self.problem(at(number), "predict question must be a top-level '1. …' item")
            for number, line, code in section(rows, "✅ Check yourself"):
                if code or "<summary>" not in line:
                    continue
                if not re.search(r"<summary>Q\d+\. ", line):
                    self.problem(at(number), "check question must read '<summary>Q1. …'")
                else:
                    self.expect(at(number), line, rf"c-{base}-{N}", "check question")
            for index, (number, line, code) in enumerate(rows):
                if not code and line.startswith("## 💬 Explain it back"):
                    self.expect(at(number + 1), line_after(index), rf"e-{base}", "explain-it-back")

    def ledger(self) -> None:
        if not LEDGER.exists():
            self.problem(str(LEDGER.relative_to(REPO_ROOT)), "missing")
            return
        issued, retired = set(), set()
        for number, raw in enumerate(LEDGER.read_text(encoding="utf-8").split("\n"), start=1):
            entry = raw.split("#", 1)[0].split()
            if not entry:
                continue
            (retired if entry[1:] == ["retired"] else issued).add(entry[0])
        for ident, where in self.found.items():
            if ident in retired:
                self.problem(where, f"'{ident}' was retired and can't be reused; take a new number")
            elif ident not in issued:
                self.problem(where, f"'{ident}' isn't in tools/issued-ids.txt; add it there")
        for ident in sorted(issued - set(self.found)):
            self.problem("tools/issued-ids.txt", f"'{ident}' no longer appears; mark it '{ident} retired'")


def main() -> int:
    checker = Checker()
    files = sorted(REPO_ROOT.glob("modules/*/*.md")) + sorted(REPO_ROOT.glob("modules/*/lab/README.md"))
    for path in files:
        if path.name != "cheatsheet.md":
            checker.file(path)
    checker.ledger()
    for problem in checker.problems:
        print(problem)
    print(f"\nChecked {len(files)} files: {len(checker.found)} IDs, {len(checker.problems)} problem(s).")
    return 1 if checker.problems else 0


if __name__ == "__main__":
    sys.exit(main())
