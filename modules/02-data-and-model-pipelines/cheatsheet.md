# Module 2 cheat sheet · Data and Model Pipelines

[Course home](../../README.md) › [Module 2](README.md) › Cheat sheet

## Pipelines and validation (2.1)

| Decision | Default | Switch when |
|---|---|---|
| Batch vs streaming | **Batch** | The decision needs data fresher than the batch interval |
| ETL vs ELT | **ELT** for tabular (keep raw) | Data must be transformed/redacted before storage, or the transforms aren't SQL (RAG) → ETL |

**Schema per column:** type · nullable · range · allowed values · **availability** (`at_decision` / `post_label` / `identifier` / `label`)

**Gate:** row-level → quarantine (fail above tolerance) · dataset-level (missing columns, duplicates, row count, label rate, **medians/distributions**) → fail the run. A gate raises; never swallow it.

## Lineage and leakage (2.2)

- Lineage record: **commit (+dirty) · data digest · env lock · params/seed · artifact link**
- File digest ≠ content digest. Never overwrite training data in place.
- **Skew** = same feature, different computation. Fix: one definition (shared code / feature store), log served features, preprocessing inside the artifact.
- **Leakage kinds:** target · temporal · group · preprocessing · train/test contamination
- **Detect:** availability contract → single-feature AUC ≥ 0.9 → too-good-to-be-true → offline/online gap
- Split time-ordered data **by time** (and by group).

## Deep-learning data paths (2.3)

- Throughput = slowest stage. Workers ≈ GPU samples/s ÷ per-worker samples/s.
- Pre-process deterministic work once (tokenize offline); shard data (100 MB–1 GB files).
- Padding: static ≫ dynamic > **bucketing + dynamic** (lab: 5.12M → 1.19M tokens).
- Augment **train only**, after splitting, label-preserving.
- DDP: full model per GPU + distributed sampler + all-reduce. **Global batch = per-device × devices × accumulation**; adjust the LR. FSDP/ZeRO when the model doesn't fit.

## Parsing and chunking (2.4)

- Parse → clean (boilerplate, **hidden comments**) → validate metadata (**fail closed**) → chunk → index.
- PDF: text layer? → simple vs layout-aware; no text layer → OCR. Read 20 parsed docs by eye.
- Chunking default: **heading-aware recursive, 10–20% overlap, contextual header** ("Title › Section").
- Choose size with an eval set. Deterministic chunk IDs + upserts + delete-by-doc on edits.

## Retrieval (2.5)

```
query+role → BM25 (filtered) ┐
           → dense (filtered) ┴→ RRF (k=60) → rerank (top 20–50) → pack (budget, sandwich, [doc_id]) → LLM → verify citations
```

- RRF(d) = Σ 1/(60 + rank). Agreement beats one first place.
- BM25 wins on exact terms (SEV1, T+2, CVV); dense wins on paraphrase.
- **Permissions:** filtered search on **every** path; never post-filter; never "via the prompt".
- Metrics: **recall@k** (found in top k?) · **MRR** (mean 1/rank of first hit). Re-run after every change.
- Lost in the middle → best chunk first, second-best last. Nothing retrieved → don't call the LLM.
- GraphRAG: global/multi-hop questions; expensive indexing; use when the eval set demands it.

## Tracking and reproducibility (2.6)

- Track params · metrics · artifacts · **lineage tags**. Nested runs for trials.
- Registry: immutable versions + movable **aliases** (`models:/name@champion`). Stages are legacy.
- Tuning: random > grid in high dimensions; TPE for expensive trials; log-scale for LR/regularisation.
- More trials can **overfit validation** (lab: val 0.102 → 0.128, test 0.099 → 0.082).
- Pickle executes code: use skops/safetensors, load only from your registry, verify digests.

## Prompt vs RAG vs fine-tune (2.7)

| Gap | First try | Then |
|---|---|---|
| **Knowledge** (facts, changing, cited, permissioned) | RAG | Better retrieval → RAFT |
| **Behaviour** (tone, format, narrow task) | Prompting + few-shot | LoRA/QLoRA → full FT |
| **Cost at volume** | Prompt a big model, measure | Distil into a small fine-tuned model |

LoRA: W' = W + (α/r)·B·A · ~0.1–1% trainable · adapter ≈ tens of MB · QLoRA = 4-bit base. **Always: evaluation set first.**

## Commands

```bash
uv run python -m pipelines.validate data/raw_baseline_20000_42.csv
uv run python -m pipelines.leakage  data/raw_baseline_20000_42.csv
uv run python -m pipelines.train [--trials N] [--seed S]
uv run python -m pipelines.registry [--score]
uv run mlflow ui --backend-store-uri sqlite:///mlflow.db
uv run python -m kestrel_docs.ingest [--show DOC_ID] [--size N --overlap M]
uv run python -m kestrel_docs.search "question" --role customer --mode hybrid [--no-rerank]
uv run python scripts/eval_retrieval.py
uv run uvicorn kestrel_docs.main:create_app --factory --port 8000
```

⬅️ [Quiz](quiz.md) · ➡️ [Module 3 · Serving and Optimization](../03-serving-and-optimization/README.md)
