# Datasheet: Kestrel Pay handbook corpus (`datasets/handbook/`)

> Filled-in example for lesson 5.6, following the question set from *Datasheets for Datasets* (Gebru et al.), shortened for an internal RAG corpus.

## Motivation

- **Why does this dataset exist?** To ground the `docs-assistant` (Track B), so answers come from approved company documents rather than the model's memory.
- **Who created it and who owns it?** Each document has an `owner` team in its front matter (Customer Support, People Team, SRE, Finance, Partnerships, Security). The AI Platform team owns the *corpus* (ingestion, indexing, access metadata).

## Composition

- 14 documents (13 Markdown, 1 HTML), about 2,000 words. Every document has `doc_id`, `title`, `access`, `owner`, `updated`.
- **Access levels:** `public` (5), `employee` (3), `engineering` (3), `hr` (2), `finance` (1).
- **Personal data:** yes. `salary-bands.md` contains a named contact with email and phone. Responses are PII-redacted; HR-level access is required to retrieve the document at all.
- **Confidential data:** salary bands (hr) and budget (finance). Must never reach users without those roles.
- **External content:** `partner-faq.md` was uploaded by an external partner (`source:` field). It is treated as **untrusted** and contains a known indirect prompt-injection payload that is kept on purpose as a regression test.

## Collection and preprocessing

- Documents are exported from the internal wiki by the owning team. There is no automated scraping.
- Ingest pipeline (`domain/documents.py`): parse front matter → strip HTML comments, hidden elements and zero-width characters → extract visible HTML text (dropping nav/footer) → chunk by heading (≤ 120 words) → every chunk inherits `access` and `trusted`.
- Sanitisation findings are logged (`ingest_flagged`) and reviewed weekly.

## Uses

- **Intended:** retrieval for the docs-assistant; the golden evaluation set (`datasets/golden/handbook_qa.jsonl`).
- **Not intended:** fine-tuning a model. HR and finance content would be memorised and could leak regardless of access control at retrieval time.

## Distribution and access

- Internal only. Retrieval enforces role → access level (see `datasets/handbook/README.md`). Index statistics are computed per permission partition.

## Maintenance

- Owners must update `updated` on each change. Documents older than 12 months are flagged for review.
- Deletion requests (e.g. GDPR erasure of the contact in `salary-bands.md`) require re-ingestion **and** cache invalidation (semantic cache, lesson 3.5). Deleting the source file alone is not enough.
