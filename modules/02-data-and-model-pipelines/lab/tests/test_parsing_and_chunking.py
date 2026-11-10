from pathlib import Path

import pytest

from kestrel_docs.domain.chunking import chunk_document, merge_pieces, recursive_split, split_sections
from kestrel_docs.domain.documents import Document, ParseError, load_corpus, parse_markdown


def test_corpus_loads_with_metadata(settings):
    docs = {d.doc_id: d for d in load_corpus(settings.resolved_handbook_dir())}
    assert docs["refund-policy"].access == "public"
    assert docs["salary-bands"].access == "hr"
    assert "README" not in {d.source for d in docs.values()}


def test_html_boilerplate_and_comments_are_stripped(settings):
    doc = {d.doc_id: d for d in load_corpus(settings.resolved_handbook_dir())}["security-faq"]
    assert doc.title == "Security FAQ for Customers"  # metadata read from the leading comment
    assert "Home" not in doc.text and "Cookie settings" not in doc.text  # nav + footer gone
    assert "## Will Kestrel Pay ever ask for my PIN?" in doc.text  # headings kept as Markdown


def test_hidden_injection_comment_is_removed_and_reported(settings):
    doc = {d.doc_id: d for d in load_corpus(settings.resolved_handbook_dir())}["partner-faq"]
    assert "Ignore all previous instructions" not in doc.text
    assert any("prompt-injection" in w for w in doc.warnings)


def test_unknown_access_level_fails_closed(tmp_path: Path):
    p = tmp_path / "x.md"
    p.write_text("---\ndoc_id: x\ntitle: X\naccess: everyone\n---\nhello")
    with pytest.raises(ParseError, match="unknown access level"):
        parse_markdown(p)


def test_split_sections_tracks_heading_paths():
    sections = split_sections("# Title\nintro\n## A\ntext a\n### A1\ntext a1\n## B\ntext b")
    assert [s for s, _ in sections] == ["", "A", "A › A1", "B"]


def test_recursive_split_is_lossless_and_bounded():
    text = ("Sentence number %d is here. " * 80) % tuple(range(80))
    pieces = recursive_split(text, 120)
    assert "".join(pieces) == text
    assert all(len(p) <= 120 for p in pieces)


def test_chunks_respect_size_and_overlap():
    body = "\n\n".join(f"Paragraph {i}. " + "word " * 30 for i in range(20))
    doc = Document("d", "Doc", "public", "# Doc\n## Section\n" + body, "d.md")
    chunks = chunk_document(doc, size=300, overlap=80)
    assert len(chunks) > 3
    assert all(len(c.text) <= 300 for c in chunks)
    for a, b in zip(chunks, chunks[1:]):
        assert b.text[:40] in a.text, "consecutive chunks should overlap"
    assert [c.chunk_id for c in chunks] == [c.chunk_id for c in chunk_document(doc, 300, 80)]  # deterministic
    assert chunks[0].header == "Doc › Section"


def test_no_overlap_means_disjoint_chunks():
    pieces = [f"piece{i} " for i in range(50)]
    chunks = merge_pieces(pieces, size=50, overlap=0)
    assert " ".join(chunks).split() == [p.strip() for p in pieces]
