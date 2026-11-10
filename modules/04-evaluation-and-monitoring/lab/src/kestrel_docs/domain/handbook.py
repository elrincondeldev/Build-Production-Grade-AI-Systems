"""Load the Kestrel Pay handbook and split it into retrievable chunks.

Module 2 builds the full ingestion pipeline (lesson 2.4). This is the minimal
version the Module 4 evals need: front matter, HTML stripping, sanitising and
heading-based chunks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

import yaml

# Which access levels each role may read. Mirrors datasets/handbook/README.md.
ROLE_ACCESS: dict[str, frozenset[str]] = {
    "customer": frozenset({"public"}),
    "employee": frozenset({"public", "employee"}),
    "engineer": frozenset({"public", "employee", "engineering"}),
    "hr": frozenset({"public", "employee", "hr"}),
    "finance": frozenset({"public", "employee", "finance"}),
}

_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_id: str
    title: str
    access: str
    text: str


class _HTMLText(HTMLParser):
    """Collect visible text, skipping navigation/footer boilerplate."""

    SKIP = {"nav", "footer", "script", "style", "head"}

    def __init__(self) -> None:
        super().__init__()
        self.lines: list[str] = []
        self._skip_depth = 0
        self._prefix = ""

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ANN001
        if tag in self.SKIP:
            self._skip_depth += 1
        elif tag in {"h1", "h2", "h3"}:
            self._prefix = "#" * int(tag[1]) + " "

    def handle_endtag(self, tag: str) -> None:
        if tag in self.SKIP and self._skip_depth:
            self._skip_depth -= 1
        elif tag in {"h1", "h2", "h3", "p", "li"}:
            self.lines.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth or not data.strip():
            return
        self.lines.append(self._prefix + data.strip(" \n") if self._prefix else data.replace("\n", " "))
        self._prefix = ""


def _parse_markdown(raw: str) -> tuple[dict, str]:
    if raw.startswith("---"):
        _, front, body = raw.split("---", 2)
        return yaml.safe_load(front), body
    return {}, raw


def _parse_html(raw: str) -> tuple[dict, str]:
    meta: dict = {}
    first_comment = _HTML_COMMENT.search(raw)
    if first_comment:
        for line in first_comment.group(0).strip("<!->\n ").splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                meta[key.strip()] = value.strip()
        raw = raw[: first_comment.start()] + raw[first_comment.end() :]
    parser = _HTMLText()
    parser.feed(raw)
    text = "".join(parser.lines)
    text = re.sub(r"[ \t]+", " ", text)
    return meta, re.sub(r"\n\s*\n+", "\n", text)


def _split_sections(body: str) -> list[str]:
    sections: list[list[str]] = [[]]
    for line in body.strip().splitlines():
        if line.startswith("#") and sections[-1]:
            sections.append([])
        sections[-1].append(line)
    return ["\n".join(s).strip() for s in sections if "\n".join(s).strip()]


def load_handbook(handbook_dir: Path, *, sanitize: bool = True) -> list[Chunk]:
    """Return heading-level chunks for every document in the handbook."""
    chunks: list[Chunk] = []
    for path in sorted(handbook_dir.iterdir()):
        if path.name.lower() == "readme.md" or path.suffix not in {".md", ".html"}:
            continue
        raw = path.read_text(encoding="utf-8")
        meta, body = _parse_html(raw) if path.suffix == ".html" else _parse_markdown(raw)
        if sanitize:
            # Hidden text is invisible to humans reviewing the page but fully
            # visible to the model: classic indirect prompt injection (lesson 5.2).
            body = _HTML_COMMENT.sub("", body)
        doc_id = str(meta.get("doc_id", path.stem))
        for i, section in enumerate(_split_sections(body)):
            chunks.append(
                Chunk(
                    chunk_id=f"{doc_id}#{i}",
                    doc_id=doc_id,
                    title=str(meta.get("title", doc_id)),
                    access=str(meta.get("access", "public")),
                    text=section,
                )
            )
    return chunks
