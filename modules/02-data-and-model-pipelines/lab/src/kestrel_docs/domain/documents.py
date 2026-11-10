"""Parsing: turn raw files (Markdown with front matter, HTML) into clean Documents. 📖 Lesson 2.4.

Parsing is where most RAG quality is won or lost. Garbage here (navigation menus,
cookie banners, hidden comments) becomes garbage the LLM confidently repeats.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from bs4 import BeautifulSoup, Comment

_FRONT_MATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)
_HTML_COMMENT = re.compile(r"<!--(.*?)-->", re.S)
ACCESS_LEVELS = {"public", "employee", "engineering", "hr", "finance"}


@dataclass
class Document:
    doc_id: str
    title: str
    access: str
    text: str  # normalised Markdown-like text: '#' headings + paragraphs
    source: str
    metadata: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


class ParseError(ValueError):
    pass


def _require(meta: dict, path: Path) -> None:
    for key in ("doc_id", "title", "access"):
        if not meta.get(key):
            raise ParseError(f"{path.name}: missing required metadata '{key}'")
    if meta["access"] not in ACCESS_LEVELS:
        # Fail closed: an unknown access level must never default to 'public'.
        raise ParseError(f"{path.name}: unknown access level {meta['access']!r}")


def parse_markdown(path: Path) -> Document:
    raw = path.read_text(encoding="utf-8")
    m = _FRONT_MATTER.match(raw)
    if not m:
        raise ParseError(f"{path.name}: no front matter")
    meta = yaml.safe_load(m.group(1)) or {}
    _require(meta, path)
    body = raw[m.end():]
    warnings = []
    comments = _HTML_COMMENT.findall(body)
    if comments:
        # Invisible when rendered, perfectly visible to an LLM: classic hiding spot
        # for indirect prompt injection (📖 lesson 5.2). Strip at ingest, and log it.
        body = _HTML_COMMENT.sub("", body)
        warnings.append(f"removed {len(comments)} hidden HTML comment(s): possible prompt-injection vector")
    return Document(
        doc_id=meta["doc_id"], title=meta["title"], access=meta["access"],
        text=re.sub(r"\n{3,}", "\n\n", body).strip(), source=path.name,
        metadata={k: str(v) for k, v in meta.items()}, warnings=warnings,
    )


def parse_html(path: Path) -> Document:
    raw = path.read_text(encoding="utf-8")
    # Our HTML files carry metadata in a leading comment. Read it BEFORE stripping comments.
    first = _HTML_COMMENT.search(raw)
    meta = yaml.safe_load(first.group(1)) if first else {}
    meta = meta if isinstance(meta, dict) else {}
    _require(meta, path)

    soup = BeautifulSoup(raw, "html.parser")
    n_comments = 0
    for c in soup.find_all(string=lambda s: isinstance(s, Comment)):
        c.extract()
        n_comments += 1
    # Boilerplate: present on every page, relevant to no question.
    for tag in soup(["nav", "footer", "header", "script", "style", "form", "aside"]):
        tag.decompose()

    root = soup.find("main") or soup.body or soup
    lines: list[str] = []
    for el in root.find_all(["h1", "h2", "h3", "h4", "p", "li", "pre", "td"]):
        text = re.sub(r"\s+([.,;:!?])", r"\1", el.get_text(" ", strip=True))  # "devices ." -> "devices."
        if not text:
            continue
        if el.name.startswith("h"):
            lines.append("\n" + "#" * int(el.name[1]) + " " + text)
        elif el.name == "li":
            lines.append("- " + text)
        else:
            lines.append(text)
    warnings = [f"removed {n_comments - 1} extra HTML comment(s)"] if n_comments > 1 else []
    return Document(
        doc_id=meta["doc_id"], title=meta["title"], access=meta["access"],
        text="\n".join(lines).strip(), source=path.name,
        metadata={k: str(v) for k, v in meta.items()}, warnings=warnings,
    )


PARSERS = {".md": parse_markdown, ".html": parse_html, ".htm": parse_html}


def load_corpus(directory: Path) -> list[Document]:
    """Parse every supported file. README files describe the corpus; they are not part of it."""
    docs = []
    for path in sorted(directory.iterdir()):
        if path.suffix.lower() in PARSERS and path.name.lower() != "readme.md":
            docs.append(PARSERS[path.suffix.lower()](path))
    ids = [d.doc_id for d in docs]
    if len(ids) != len(set(ids)):
        raise ParseError(f"duplicate doc_id values in corpus: {ids}")
    return docs
