# Module 1 · From Prototype to Production

> ⏱ ~10 hours (5 lessons ≈ 4.5 h + lab ≈ 3–4 h + quiz) · Track A: `fraud-service`

[Course home](../../README.md) › Module 1

## 🧭 Where you are

```mermaid
flowchart LR
    M0["0 · Foundations"] --> M1["1 · Prototype → Production"] --> M2["2 · Data & Model Pipelines"] --> M3["3 · Serving & Optimization"] --> M4["4 · Evaluation & Monitoring"] --> M5["5 · Security & Governance"] --> M6["6 · Scaling & Operations"] --> C["🏆 Capstone"]
    classDef done fill:#d1fae5,stroke:#059669,color:#064e3b
    classDef here fill:#fde68a,stroke:#d97706,stroke-width:3px,color:#78350f
    class M0 done
    class M1 here
```

## 📨 The story so far

> **From: Maya (Engineering Manager)**
> Week one! Sam's fraud notebook impressed leadership, and Risk wants it scoring live card transactions by the end of the month.
> Before that happens, I need it to be something we can **trust and operate**: reproducible, versioned, observable, resilient to failures, and packaged so Diego's team can deploy it.
> Sam thinks it "just needs an API around it". I suspect it needs a bit more than that. Over to you.

In this module you take Sam's notebook and turn it into a **versioned, layered, containerised service** that degrades gracefully when things break. The same habits apply to every AI system you'll build afterwards, including the LLM-based `docs-assistant` from Module 2 onwards.

## 🎯 Module objectives

By the end of this module you can:

1. **Explain** what separates a prototype from a production AI system, and **draw** the AI lifecycle for classic ML and LLM apps.
2. **Detect and prevent** training/serving skew and label leakage.
3. **Choose** between batch, online and streaming inference, and between monolith, microservices and event-driven designs, using a latency budget.
4. **Implement** timeouts, retries with exponential backoff and jitter, deadlines, retry budgets and graceful degradation.
5. **Structure** a FastAPI service into API, domain and adapter layers with typed config, separated secrets, async I/O, request IDs, structured logs and health/readiness endpoints.
6. **Package** a model as an immutable, sha256-verified artifact and ship it in a multi-stage, non-root container that Kubernetes can run.

## 📖 Lessons

| # | Lesson | You'll learn | Time |
|---|---|---|---|
| 1.1 | [Prototype vs production and the AI lifecycle](01-prototype-vs-production.md) | What changes in production; the two tracks; the lifecycle; training/serving skew; handoff artifacts | 45 min |
| 1.2 | [Architecture patterns for AI systems](02-architecture-patterns.md) | Batch vs online vs streaming; monolith vs microservices vs event-driven; gateways, feature stores, vector DBs, model registries; latency budgets | 50 min |
| 1.3 | [Reliability primitives](03-reliability-primitives.md) | Timeouts, deadlines, retries, backoff, jitter, retry budgets, queues, graceful degradation; REST vs gRPC; streaming responses | 60 min |
| 1.4 | [Building production services](04-production-services.md) | Layered architecture; config and secrets; async I/O; request IDs; structured logs; liveness, readiness, startup | 60 min |
| 1.5 | [Artifacts, Docker and Kubernetes](05-artifacts-and-containers.md) | Serialization formats and risks; versioned artifacts with sha256; Docker layers and multi-stage builds; Kubernetes objects | 60 min |

**Suggested order:** read 1.1 → do Lab steps 1–3 → read 1.2 and 1.3 → do Lab steps 4–8 → read 1.4 and 1.5 → do Lab steps 9–10 → quiz.

## 🛠 Lab 1: Ship the fraud model as a containerised service

📂 [`lab/`](lab/README.md) · ⏱ 3–4 hours · runs offline on a laptop CPU

You'll review Sam's prototype and find its problems, train a reproducible versioned artifact, run a layered FastAPI service, survive a deliberately flaky dependency with retries and graceful degradation, stream an LLM explanation over Server-Sent Events, and build a hardened Docker image with Kubernetes manifests ready for Module 6.

```bash
cd modules/01-prototype-to-production/lab
uv sync && uv run python scripts/train.py && uv run pytest
```

### ✅ Definition of Done

- [ ] I listed at least 10 problems in `prototype/sam_notebook.py` and know which lesson addresses each
- [ ] `scripts/train.py` produces an immutable version folder with `model.joblib` and a complete `metadata.json`, and I can prove two runs are bit-identical
- [ ] `uv run pytest` passes (32 tests)
- [ ] I traced one request ID from `curl` through the service and into the feature-store logs
- [ ] With the feature store failing 100% of the time, `/v1/score` still returns 200 with `degraded: true`, and retries stop when the budget is exhausted
- [ ] With a tampered artifact: `/health` 200, `/ready` 503, scoring falls back to rules
- [ ] The Docker image builds, runs as a non-root user, and reports `(healthy)`
- [ ] I can explain every field in `k8s/deployment.yaml`
- [ ] I completed at least 3 "Break it" experiments and 1 "Extend it" exercise
- [ ] I scored at least 80% on the [module quiz](quiz.md)

## 📊 Self-assessment

Rate yourself before and after the module. Aim for **3+** on everything before moving on. Anything at 1–2 after the lab, reread that lesson's 🔑 takeaways and redo its 🧪 Try it.

| Skill | 1 · Never heard of it | 2 · Recognise it | 3 · Can do it with notes | 4 · Could teach it |
|---|---|---|---|---|
| Explaining training/serving skew and leakage | | | | |
| Drawing the AI lifecycle for both tracks | | | | |
| Choosing batch vs online vs streaming | | | | |
| Writing a latency budget | | | | |
| Timeouts, retries, backoff, jitter, budgets | | | | |
| Designing a graceful-degradation ladder | | | | |
| REST vs gRPC, SSE streaming | | | | |
| Layered (ports and adapters) service structure | | | | |
| Typed config and secret handling | | | | |
| Async I/O and avoiding event-loop blocking | | | | |
| Request IDs and structured logs | | | | |
| Liveness vs readiness vs startup probes | | | | |
| Versioned artifacts with sha256 | | | | |
| Multi-stage, non-root Dockerfiles | | | | |
| Reading a Kubernetes Deployment and Service | | | | |

## 🎤 Interview corner

These come up in ML/AI system design and MLOps interviews. Try answering out loud in 3–5 minutes each, then check against the lessons.

1. **"A data scientist hands you a notebook with a great model. Walk me through getting it to production."** *(Lessons 1.1 and 1.5: reproducibility, leakage check, artifact + metadata, API contract, packaging, monitoring plan.)*
2. **"Design a real-time fraud detection system with a 150 ms p99 budget. What happens when the feature store is slow?"** *(Lessons 1.2 and 1.3: latency budget, timeouts, bounded retries, fallback ladder, fail-open vs fail-closed as a business decision.)*
3. **"What is training/serving skew? Give examples and how you'd prevent it."** *(Lesson 1.1: two code paths, leakage, freshness, versions; shared feature code, feature contracts, logging served features, feature stores.)*
4. **"How do you make retries safe?"** *(Lesson 1.3: retryable errors only, idempotency keys, exponential backoff + jitter, single retry layer, deadlines, retry budgets, circuit breakers.)*
5. **"What's the difference between liveness and readiness probes, and what goes wrong if you check the database in liveness?"** *(Lesson 1.4: restart loops during dependency outages.)*

## 🧰 Extras

- 📝 [Module 1 quiz](quiz.md): 14 questions, including spaced review from Module 0
- 📄 [Module 1 cheat sheet](cheatsheet.md): one page to review before Module 2 and before interviews
- 🗂 Templates you can reuse: see [`templates/`](../../templates/) (design doc, ADR, runbook)

---
⬅️ [Module 0: Foundations](../00-foundations/README.md) · ➡️ [Module 2: Data and Model Pipelines](../02-data-and-model-pipelines/README.md)
