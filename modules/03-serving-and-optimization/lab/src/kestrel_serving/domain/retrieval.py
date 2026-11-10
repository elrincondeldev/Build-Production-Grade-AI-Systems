"""Deliberately simple retrieval over the Kestrel handbook.

Module 2 builds proper hybrid retrieval. Here retrieval only needs to be *cheap and
predictable* so that the thing we measure in Module 3 is the serving path.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from kestrel_serving.adapters.embeddings import Embedder

_FRONT_MATTER = re.compile(r"^---\n(.*?)\n---\n", re.S)
_HTML_COMMENT = re.compile(r"<!--(.*?)-->", re.S)
_TAG = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class Chunk:
    doc_id: str
    title: str
    text: str


def _parse_meta(block: str) -> dict[str, str]:
    meta = {}
    for line in block.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip()
    return meta


def load_handbook(handbook_dir: Path) -> list[Chunk]:
    chunks: list[Chunk] = []
    for path in sorted(handbook_dir.glob("*")):
        if path.name == "README.md" or path.suffix not in {".md", ".html"}:
            continue
        raw = path.read_text(encoding="utf-8")
        if path.suffix == ".md":
            match = _FRONT_MATTER.match(raw)
            meta = _parse_meta(match.group(1)) if match else {}
            body = raw[match.end():] if match else raw
            body = _HTML_COMMENT.sub("", body)  # hidden comments are not content (📖 lesson 5.2)
        else:
            first_comment = _HTML_COMMENT.search(raw)
            meta = _parse_meta(first_comment.group(1)) if first_comment else {}
            main = re.search(r"<main>(.*?)</main>", raw, re.S)
            body = _TAG.sub(" ", _HTML_COMMENT.sub("", main.group(1) if main else raw))
        doc_id = meta.get("doc_id", path.stem)
        title = meta.get("title", path.stem)
        for para in re.split(r"\n\s*\n", body):
            text = re.sub(r"[ \t]+", " ", para).strip()
            if len(text) > 40:
                chunks.append(Chunk(doc_id, title, text))
    return chunks


class Retriever:
    def __init__(self, chunks: list[Chunk], embedder: Embedder) -> None:
        self.chunks = chunks
        self.embedder = embedder
        self._matrix = embedder.embed([f"{c.title} {c.text}" for c in chunks])

    def search(self, query: str, k: int = 3) -> list[Chunk]:
        scores = self._matrix @ self.embedder.embed([query])[0]
        return [self.chunks[i] for i in np.argsort(-scores)[:k]]
