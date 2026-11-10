"""Heading-aware recursive chunking with overlap. 📖 Lesson 2.4.

Strategy:
1. Split the document into **sections** at Markdown headings, so a chunk never
   mixes "Eligibility" with "Limits".
2. Inside a section, split **recursively**: paragraphs, then lines, then
   sentences, then words, until every piece fits in `size` characters.
3. **Merge** pieces greedily back into chunks of up to `size` characters,
   carrying the last ~`overlap` characters into the next chunk so a fact that
   straddles a boundary is complete in at least one chunk.
4. Prefix each chunk's *embedding text* with "Title › Section" (a contextual
   header) so a chunk like "Within 60 days." still says what it is about.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from kestrel_docs.domain.documents import Document

SEPARATORS = ("\n\n", "\n", ". ", " ")
_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_id: str
    title: str
    access: str
    section: str
    text: str
    position: int

    @property
    def header(self) -> str:
        return f"{self.title} › {self.section}" if self.section else self.title

    @property
    def embed_text(self) -> str:
        return f"{self.header}\n{self.text}"


def split_sections(text: str) -> list[tuple[str, str]]:
    """Return [(section_path, body)], where section_path is like 'Eligibility' or 'Timelines › Appeals'."""
    sections: list[tuple[str, str]] = []
    stack: list[tuple[int, str]] = []
    body: list[str] = []

    def flush() -> None:
        content = "\n".join(body).strip()
        if content:
            path = " › ".join(name for level, name in stack if level > 1)  # H1 is the title
            sections.append((path, content))
        body.clear()

    for line in text.splitlines():
        m = _HEADING.match(line)
        if m:
            flush()
            level, name = len(m.group(1)), m.group(2).strip()
            stack = [(lv, n) for lv, n in stack if lv < level] + [(level, name)]
        else:
            body.append(line)
    flush()
    return sections


def recursive_split(text: str, size: int, separators: tuple[str, ...] = SEPARATORS) -> list[str]:
    """Split into pieces of at most `size` chars, preferring the coarsest separator. Lossless: ''.join(pieces) == text."""
    if len(text) <= size:
        return [text]
    for i, sep in enumerate(separators):
        if sep in text:
            parts = text.split(sep)
            pieces = [p + sep for p in parts[:-1]] + [parts[-1]]
            out: list[str] = []
            for p in pieces:
                if not p:
                    continue
                out.extend(recursive_split(p, size, separators[i + 1:]) if len(p) > size else [p])
            return out
    return [text[i:i + size] for i in range(0, len(text), size)]  # no separator left: hard cut


def merge_pieces(pieces: list[str], size: int, overlap: int) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    length = 0
    for piece in pieces:
        if current and length + len(piece) > size:
            emitted = "".join(current)
            chunks.append(emitted.strip())
            # Keep whole trailing pieces of the previous chunk as overlap, but never
            # so much that the next chunk could exceed `size`.
            while current and (length > overlap or length + len(piece) > size):
                length -= len(current.pop(0))
            if not current and overlap:
                # Pieces were too big to carry over whole: fall back to the last
                # `overlap` characters, starting at a word boundary.
                tail = emitted.rstrip()[-overlap:]
                tail = tail[tail.find(" ") + 1:] if " " in tail else tail
                if tail and len(tail) + 1 + len(piece) <= size:
                    current, length = [tail + "\n"], len(tail) + 1
        current.append(piece)
        length += len(piece)
    if current:
        chunks.append("".join(current).strip())
    return [c for c in chunks if c]


def chunk_document(doc: Document, size: int = 600, overlap: int = 100) -> list[Chunk]:
    if overlap >= size:
        raise ValueError("overlap must be smaller than size")
    chunks: list[Chunk] = []
    for section, body in split_sections(doc.text):
        for text in merge_pieces(recursive_split(body, size), size, overlap):
            n = len(chunks)
            chunks.append(Chunk(f"{doc.doc_id}#{n:03d}", doc.doc_id, doc.title, doc.access, section, text, n))
    return chunks
