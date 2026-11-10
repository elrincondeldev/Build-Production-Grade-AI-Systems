"""Check that every relative link in the course's Markdown files points to a real file.

    python3 tools/check_links.py

External (http/https) links are not fetched; this keeps the check fast and offline.
Exits non-zero if any relative link is broken, so it can run in CI.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
SKIP_DIRS = {".git", ".venv", "node_modules", ".pytest_cache"}


def iter_markdown() -> list[Path]:
    return [p for p in REPO_ROOT.rglob("*.md") if not SKIP_DIRS.intersection(p.parts)]


def main() -> int:
    broken: list[str] = []
    files = iter_markdown()
    for md in files:
        text = md.read_text(encoding="utf-8")
        # ignore links inside fenced code blocks
        text = re.sub(r"```.*?```", "", text, flags=re.S)
        for target in LINK.findall(text):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            path = target.split("#", 1)[0]
            if not path:
                continue
            if not (md.parent / path).resolve().exists():
                broken.append(f"{md.relative_to(REPO_ROOT)} → {target}")
    for b in broken:
        print(f"✘ {b}")
    print(f"\nChecked {len(files)} Markdown files: {len(broken)} broken relative link(s).")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
