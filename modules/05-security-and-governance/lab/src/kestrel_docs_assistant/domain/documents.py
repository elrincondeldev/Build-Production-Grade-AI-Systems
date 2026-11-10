"""Load the handbook, parse metadata, and sanitise content at ingest time.

📖 See lessons 2.4 (parsing) and 5.2 (indirect prompt injection).

Ingest is the cheapest place to stop an attack: whatever you strip here can never
reach a prompt. We remove content a *human reader would not see* but a model would:
HTML comments, zero-width characters and elements hidden with CSS. We also record
**provenance**: any document with a ``source:`` field came from outside the
company and is marked untrusted.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

_FRONT_MATTER_RE = re.compile(r"\A---\s*\n(?P<meta>.*?)\n---\s*\n(?P<body>.*)\Z", re.S)
_HTML_META_RE = re.compile(r"\A\s*<!--(?P<meta>.*?)-->\s*(?P<body>.*)\Z", re.S)
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
_ZERO_WIDTH_RE = re.compile("[​‌‍⁠﻿]")
_HIDDEN_ELEMENT_RE = re.compile(
    r"<(?P<tag>[a-zA-Z][a-zA-Z0-9]*)\b[^>]*(?:display\s*:\s*none|visibility\s*:\s*hidden|\shidden\b)[^>]*>.*?</(?P=tag)>",
    re.S | re.I,
)


@dataclass(frozen=True)
class Document:
    doc_id: str
    title: str
    access: str
    owner: str
    updated: str
    source: str | None
    text: str
    path: Path
    findings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def trusted(self) -> bool:
        # Provenance rule: anything not authored inside Kestrel Pay is untrusted data.
        return self.source is None


def _parse_meta(block: str) -> dict[str, str]:
    meta: dict[str, str] = {}
    for line in block.strip().splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip()
    return meta


def sanitize(text: str) -> tuple[str, list[str]]:
    """Remove content invisible to humans. Returns (clean_text, findings)."""
    findings: list[str] = []
    if _HTML_COMMENT_RE.search(text):
        findings.append("html_comment_removed")
        text = _HTML_COMMENT_RE.sub("", text)
    if _HIDDEN_ELEMENT_RE.search(text):
        findings.append("hidden_element_removed")
        text = _HIDDEN_ELEMENT_RE.sub("", text)
    if _ZERO_WIDTH_RE.search(text):
        findings.append("zero_width_chars_removed")
        text = _ZERO_WIDTH_RE.sub("", text)
    return re.sub(r"\n{3,}", "\n\n", text), findings


class _VisibleTextParser(HTMLParser):
    """Keep main content; drop navigation, footers, scripts and styles (boilerplate)."""

    SKIP = {"nav", "footer", "script", "style", "head", "noscript"}
    BLOCK = {"p", "li", "h1", "h2", "h3", "h4", "div", "section", "tr", "br"}

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip_depth = 0
        self._heading: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.SKIP:
            self._skip_depth += 1
        elif tag in {"h1", "h2", "h3"}:
            self._heading = tag
            self.parts.append("\n" + "#" * int(tag[1]) + " ")
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.SKIP and self._skip_depth:
            self._skip_depth -= 1
        elif tag in self.BLOCK or tag == self._heading:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self.parts.append(re.sub(r"\s+", " ", data))

    def text(self) -> str:
        lines = [line.strip() for line in "".join(self.parts).splitlines()]
        return "\n\n".join(line for line in lines if line)


def html_to_text(html: str) -> str:
    parser = _VisibleTextParser()
    parser.feed(html)
    return parser.text()


def load_document(path: Path, *, sanitize_content: bool = True) -> Document:
    raw = path.read_text(encoding="utf-8")
    if path.suffix == ".html":
        match = _HTML_META_RE.match(raw)
        if not match:
            raise ValueError(f"{path.name}: missing metadata comment")
        meta, body = _parse_meta(match["meta"]), match["body"]
        findings: list[str] = []
        if sanitize_content:
            body, findings = sanitize(body)
        text = html_to_text(body)
    else:
        match = _FRONT_MATTER_RE.match(raw)
        if not match:
            raise ValueError(f"{path.name}: missing front matter")
        meta, body = _parse_meta(match["meta"]), match["body"]
        findings = []
        if sanitize_content:
            body, findings = sanitize(body)
        text = body.strip()

    for required in ("doc_id", "title", "access"):
        if required not in meta:
            raise ValueError(f"{path.name}: front matter missing {required!r}")

    return Document(
        doc_id=meta["doc_id"],
        title=meta["title"],
        access=meta["access"],
        owner=meta.get("owner", "unknown"),
        updated=meta.get("updated", "unknown"),
        source=meta.get("source"),
        text=text,
        path=path,
        findings=tuple(findings),
    )


def load_corpus(handbook_dir: Path, *, sanitize_content: bool = True) -> list[Document]:
    paths = sorted(p for p in handbook_dir.iterdir() if p.suffix in {".md", ".html"} and p.name != "README.md")
    return [load_document(p, sanitize_content=sanitize_content) for p in paths]


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_id: str
    title: str
    access: str
    trusted: bool
    text: str


def chunk_document(doc: Document, *, max_words: int = 120) -> list[Chunk]:
    """Split by headings, then by paragraphs when a section is too long.

    Every chunk *inherits the document's access level and trust*. Losing that
    metadata during chunking is how permission leaks happen (📖 lesson 5.3).
    """
    sections = re.split(r"\n(?=#{1,3} )", "\n" + doc.text)
    pieces: list[str] = []
    for section in (s.strip() for s in sections):
        if not section:
            continue
        if len(section.split()) <= max_words:
            pieces.append(section)
            continue
        buffer: list[str] = []
        for para in section.split("\n\n"):
            if buffer and len(" ".join(buffer + [para]).split()) > max_words:
                pieces.append("\n\n".join(buffer))
                buffer = []
            buffer.append(para)
        if buffer:
            pieces.append("\n\n".join(buffer))

    return [
        Chunk(
            chunk_id=f"{doc.doc_id}#{i}",
            doc_id=doc.doc_id,
            title=doc.title,
            access=doc.access,
            trusted=doc.trusted,
            text=piece,
        )
        for i, piece in enumerate(pieces)
    ]
