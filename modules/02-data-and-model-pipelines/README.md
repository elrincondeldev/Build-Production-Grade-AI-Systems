# Module 2 · Data and Model Pipelines

> ⏱ ~14 h (7 lessons × 45–60 min + a 4–5 h lab) · 🎚 Core · 🧰 Needs: [Module 1](../01-prototype-to-production/README.md) (or comfort with FastAPI and Python packaging)

[Course home](../../README.md) › Module 2

## 🧭 Where you are

```mermaid
flowchart LR
    M0["0 · Foundations"] --> M1["1 · Prototype → Production"] --> M2["2 · Data & Model Pipelines"] --> M3["3 · Serving & Optimization"] --> M4["4 · Evaluation & Monitoring"] --> M5["5 · Security & Governance"] --> M6["6 · Scaling & Operations"] --> C["🏆 Capstone"]
    classDef done fill:#d1fae5,stroke:#059669,color:#064e3b
    classDef here fill:#fde68a,stroke:#d97706,stroke-width:3px,color:#78350f
    class M0,M1 done
    class M2 here
```

## 📨 The story so far

> **From: Maya (Engineering Manager)**
> Great work getting `fraud-service` into a container last module. Two problems landed on my desk this week:
>
> 1. **Omar (Risk)** says the fraud model "looked amazing in Sam's notebook and is mediocre in production". Nobody can say which data it was trained on, and Sam can't reproduce the notebook result.
> 2. **Lena (Support)** tried the docs-assistant prototype. It answered a customer question with a line from the *salary bands* document and quoted a "policy" nobody recognises.
>
> Both are data problems wearing model costumes. This module is about the pipelines *around* the model: what goes in, how we know it's good, and how we rebuild any result on demand.

## 🎯 By the end of this module you can

- **Design** an ingestion pipeline and choose between batch and streaming, ETL and ELT, for a given use case.
- **Implement** a validation gate that stops a pipeline on bad data, and **explain** row-level vs dataset-level checks.
- **Detect** data leakage with a feature-availability contract and a statistical check, and **prevent** training/serving skew.
- **Describe** how deep-learning data paths work (loaders, batching, augmentation, distributed data parallelism) and where they bottleneck.
- **Build** a RAG ingestion pipeline: parse PDF/HTML/Markdown, chunk with headings and overlap, index with metadata, upsert idempotently.
- **Implement** hybrid retrieval (BM25 + dense vectors + Reciprocal Rank Fusion + reranking) with permission filters and **measure** it with recall@k and MRR.
- **Package** context under a token budget with ordering and verifiable citations, and **explain** when GraphRAG helps.
- **Track** experiments in MLflow, **register** models with aliases, **tune** hyperparameters, and **rebuild** any model from its commit, data digest and lock file.
- **Choose** between prompting, RAG, PEFT/LoRA and full fine-tuning with a defensible argument.

## 📖 Lessons

| # | Lesson | What you'll learn | ⏱ |
|---|---|---|---|
| 2.1 | [Data pipelines and validation gates](01-data-pipelines-and-validation.md) | Batch vs streaming, ETL vs ELT, schemas, row and dataset checks, quarantine | 50 min |
| 2.2 | [Lineage, versioning and leakage](02-lineage-versioning-and-leakage.md) | Digests, lineage records, training/serving parity, temporal splits, leakage detection | 55 min |
| 2.3 | [Deep-learning data paths](03-deep-learning-data-paths.md) | Datasets and loaders, batching and padding, augmentation, distributed data parallel | 45 min |
| 2.4 | [Document parsing and chunking](04-document-parsing-and-chunking.md) | PDF, HTML and OCR parsing, boilerplate removal, chunking strategies, contextual headers | 55 min |
| 2.5 | [Vector search and hybrid retrieval](05-vector-search-and-hybrid-retrieval.md) | Vector DB operations, ANN, BM25 + dense + RRF + rerank, context packaging, citations, GraphRAG | 60 min |
| 2.6 | [Experiment tracking and reproducibility](06-experiment-tracking-and-reproducibility.md) | MLflow runs, registry stages vs aliases, hyperparameter tuning, the reproducibility checklist | 50 min |
| 2.7 | [Prompt, RAG or fine-tune?](07-prompt-rag-or-fine-tune.md) | A decision framework: prompting vs RAG vs PEFT/LoRA vs full fine-tuning | 45 min |

## 🛠 Lab 2: two pipelines you can trust

[**Open the lab →**](lab/README.md) · ⏱ 4–5 h

| Part | Track | You build |
|---|---|---|
| **A** | `fraud-service` | `generate → validate gate → leakage check → temporal split → Optuna tuning → MLflow tracking → registry @champion` |
| **B** | `docs-assistant` | `parse (MD + HTML) → heading-aware chunking → hash/semantic embeddings → Qdrant upserts with access metadata → BM25 + dense + RRF + rerank → context packing → cited answers on POST /v1/ask` |

### ✅ Definition of Done

- [ ] `uv run pytest` passes (33 tests) in `lab/`.
- [ ] You saw the validation gate **fail** on bad data and can explain the difference between quarantining rows and failing the run.
- [ ] You ran the leakage scan and can explain why `chargeback_filed` scores ROC-AUC ≈ 0.92 on its own and why that is a red flag rather than a win.
- [ ] You trained at least two models, opened them in the MLflow UI, and found the data digest and git commit for each.
- [ ] You loaded the model by alias (`models:/fraud-classifier@champion`), not by version number.
- [ ] You ran `scripts/eval_retrieval.py` and can explain the recall@k / MRR differences between BM25, dense and hybrid.
- [ ] You asked `/v1/ask` the same question with role `customer` and role `hr` and saw different retrieved chunks.
- [ ] You filled in [`lab/REPRODUCIBILITY.md`](lab/REPRODUCIBILITY.md) for one of your runs.

## 📊 Self-assessment

Rate yourself before and after the module. 1 = never heard of it · 2 = I recognise the term · 3 = I can do it with notes · 4 = I could teach it.

| Skill | Before | After |
|---|---|---|
| Choosing batch vs streaming and ETL vs ELT | | |
| Writing a validation gate with row- and dataset-level checks | | |
| Explaining and detecting data leakage and training/serving skew | | |
| Explaining DataLoader workers, padding and DDP | | |
| Parsing HTML/PDF and choosing a chunking strategy | | |
| Building hybrid retrieval with RRF and a reranker | | |
| Measuring retrieval with recall@k and MRR | | |
| Packaging context with a token budget and verifiable citations | | |
| Tracking runs and using a model registry with aliases | | |
| Rebuilding a model from commit + data digest + lock file | | |
| Arguing prompt vs RAG vs LoRA vs full fine-tuning for a use case | | |

## 🎤 Interview corner

These come up in ML and AI system design interviews. Try answering out loud in 3–5 minutes each, then compare with the lessons.

1. *"Design the data pipeline for a fraud model that scores transactions in real time. How do you make sure training features match serving features?"* (lessons 2.1, 2.2)
2. *"Your new model's offline AUC jumped from 0.84 to 0.94. What do you check before celebrating?"* (lesson 2.2)
3. *"Design a RAG system over 2 million internal documents with per-team permissions. Walk me through ingestion, indexing, retrieval and how you prevent leaking documents across teams."* (lessons 2.4, 2.5)
4. *"Keyword search or vector search?"* (The strong answer is "both, fused", with a measurement plan; lesson 2.5.)
5. *"A teammate's model can't be reproduced. What would you put in place so it never happens again?"* (lesson 2.6)
6. *"Support wants the assistant to use our tone and our product knowledge. Fine-tune or RAG?"* (lesson 2.7)

## 📝 After the module

- [Module quiz](quiz.md) (15 questions, includes spaced review from Modules 0–1)
- [Cheat sheet](cheatsheet.md) (one page to revisit before interviews)

---
⬅️ [Module 1 · From Prototype to Production](../01-prototype-to-production/README.md) · ➡️ [Lesson 2.1 · Data pipelines and validation gates](01-data-pipelines-and-validation.md)
