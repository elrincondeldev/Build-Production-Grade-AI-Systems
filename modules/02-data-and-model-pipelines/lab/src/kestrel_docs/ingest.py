"""Inspect what ingestion produces.

    uv run python -m kestrel_docs.ingest                      # per-document summary
    uv run python -m kestrel_docs.ingest --show refund-policy # print that document's chunks
"""

from __future__ import annotations

import argparse

from kestrel_docs.config import get_settings
from kestrel_docs.domain.chunking import chunk_document
from kestrel_docs.domain.documents import load_corpus


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--show", help="doc_id whose chunks to print")
    parser.add_argument("--size", type=int, default=None)
    parser.add_argument("--overlap", type=int, default=None)
    args = parser.parse_args()
    s = get_settings()
    size, overlap = args.size or s.chunk_size, args.overlap if args.overlap is not None else s.chunk_overlap
    docs = load_corpus(s.resolved_handbook_dir())
    total = 0
    print(f"{'doc_id':<28} {'access':<12} {'chars':>6} {'chunks':>6}  warnings")
    for d in docs:
        chunks = chunk_document(d, size, overlap)
        total += len(chunks)
        print(f"{d.doc_id:<28} {d.access:<12} {len(d.text):>6} {len(chunks):>6}  {'; '.join(d.warnings)}")
        if args.show == d.doc_id:
            for c in chunks:
                print(f"\n  ── {c.chunk_id} [{c.header}] ({len(c.text)} chars)\n  " + c.text.replace("\n", "\n  "))
            print()
    print(f"\n{len(docs)} documents → {total} chunks (size={size}, overlap={overlap})")


if __name__ == "__main__":
    main()
