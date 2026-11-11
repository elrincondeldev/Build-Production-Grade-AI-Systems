# Module 6 quiz: Scaling and Operations

[Course home](../../README.md) › [Module 6](README.md) › Quiz

Answer each question **before** opening the answer. Write your answers down; retrieval only works if you actually try. Questions marked 🔁 are spaced review from earlier modules.

Scoring: 12–14 correct → move on to the capstone. 9–11 → re-read the takeaways of the lessons you missed. Below 9 → redo the lab steps for those lessons. <!-- pass: 12 -->

---

**1.** Your LLM server takes ~2 minutes to load its weights. Which probe stops Kubernetes from killing it during startup, and what must liveness *not* check? <!-- id: q-6-1 -->

<details><summary>Answer</summary>

A **startupProbe** with enough budget (e.g. `periodSeconds: 5`, `failureThreshold: 30`); liveness checks are disabled until it succeeds. Liveness must not check **dependencies** (database, vector DB, LLM API): a dependency blip would restart every pod at once. *(Lesson 6.1)*

</details>

**2.** A pod is failing its readiness probe but passing liveness. What happens to it? <!-- id: q-6-2 -->

<details><summary>Answer</summary>

It keeps running (no restart) but is removed from the Service's endpoints, so it receives no traffic until readiness passes again. *(Lesson 6.1)*

</details>

**3.** A small team, all on AWS, runs four stateless APIs and has no Kubernetes experience. Kubernetes, ECS or a managed ML platform for the APIs? Justify in one sentence. <!-- id: q-6-3 -->

<details><summary>Answer</summary>

ECS with Fargate is a strong default: fewer concepts and no cluster or nodes to manage, and the team doesn't need the Kubernetes ecosystem (GPU scheduling, Argo, KEDA) yet. *(Lesson 6.1)*

</details>

**4.** Which two properties must a pipeline task have so that retries and backfills are safe? <!-- id: q-6-4 -->

<details><summary>Answer</summary>

It must be **idempotent** (running it twice equals running it once) and driven by **explicit inputs** (e.g. a date partition), writing atomically (new version, then flip a pointer) rather than mutating shared state. *(Lesson 6.2)*

</details>

**5.** True or false: "Ray replaces Airflow." <!-- id: q-6-5 -->

<details><summary>Answer</summary>

False. Ray is a distributed compute engine (tasks, actors, Train/Tune/Serve). Airflow is a workflow scheduler (dependencies, scheduling, backfills, run history). They're often combined: the orchestrator triggers a Ray job for the heavy step. *(Lesson 6.2)*

</details>

**6.** 15 requests/s, 800 input and 300 output tokens, prefill 20,000 tok/s and decode 2,500 tok/s per replica, target utilisation 0.6, minimum 2 replicas. How many replicas at peak? <!-- id: q-6-6 -->

<details><summary>Answer</summary>

GPU-s = 800/20,000 + 300/2,500 = 0.04 + 0.12 = 0.16 s. Busy = 15 × 0.16 = 2.4. Replicas = ceil(2.4 / 0.6) = **4**. *(Lesson 6.3)*

</details>

**7.** Why is GPU utilisation a poor autoscaling signal for a vLLM server, and what should you use instead? <!-- id: q-6-7 -->

<details><summary>Answer</summary>

With continuous batching the GPU looks busy at many load levels; utilisation shows kernels running, not spare capacity. Scale on **queue depth (waiting requests)**, **in-flight requests per replica** or **KV-cache usage**. *(Lesson 6.3)*

</details>

**8.** Canary analysis: 0 errors in 150 requests, limit 1%. Promote? Why or why not? <!-- id: q-6-8 -->

<details><summary>Answer</summary>

**Hold.** The 95% upper bound with 0/150 is about 2.5%, so you can't yet claim the true rate is below 1%. You need roughly 380+ clean requests ("pass slow"). *(Lesson 6.4)*

</details>

**9.** 99.9% SLO over 30 days. The last hour had a 2% error rate and the last 5 minutes 3%. Which alert fires, and how much budget does a sustained hour at this rate consume? <!-- id: q-6-9 -->

<details><summary>Answer</summary>

Burn rates are 20× (1h) and 30× (5m), both ≥ 14.4, so the **fast-burn page** fires. One hour at burn 20 consumes 20 × 1/720 ≈ **2.8%** of the monthly budget. *(Lesson 6.4)*

</details>

**10.** At 03:00 fraud-service latency is burning its SLO and a model was deployed 3 hours ago. What's the first action, and who should be doing what once a second engineer joins? <!-- id: q-6-10 -->

<details><summary>Answer</summary>

**Mitigate first**: roll back the model (the runbook's first row), then diagnose. With two people, split roles: one is **Incident Commander** (coordinates, decides, communicates or delegates comms), the other is **Operations** (executes the rollback and checks). *(Lesson 6.5)*

</details>

**11.** Name two AI-specific incidents that error-rate and latency dashboards cannot detect, and one signal for each. <!-- id: q-6-11 -->

<details><summary>Answer</summary>

For example: a hallucination spike → groundedness judge on sampled traffic; a retrieval failure or stale index → retrieval hit rate or "no documents found" rate; a cost runaway → tokens/min or €/hour against budget; prompt injection → guardrail block counts and unusual tool calls. *(Lesson 6.5)*

</details>

**12.** The refund agent's system prompt says "never refund more than €50 without approval". Priya says that's not a control. What is the control, and where does it live? <!-- id: q-6-12 -->

<details><summary>Answer</summary>

A deterministic **approval gate** in the runtime (`gate_refund`) that the model can't see or change, plus least-privilege limits enforced again by the payments API. The prompt is guidance; the code is the control. *(Lesson 6.6)*

</details>

**13.** 🔁 *(Modules 2 and 4)* Why does the lab's training pipeline gate on PR-AUC relative to the base rate instead of an absolute threshold, and which metric would you *not* use for this problem? <!-- id: q-6-13 -->

<details><summary>Answer</summary>

With ~1.4% fraud, a random model scores PR-AUC ≈ base rate, and the achievable maximum on this noisy data is only ~0.10, so an absolute threshold is either meaningless or impossible. A **lift over the base rate** is comparable across fraud rates. Don't use **accuracy**: predicting "never fraud" scores 98.6%.

</details>

**14.** 🔁 *(Module 5)* A partner uploads a FAQ containing hidden instructions telling the assistant to ask customers for their CVV. Name three defences from Module 5 and the operational step from this module once it's discovered in production. <!-- id: q-6-14 -->

<details><summary>Answer</summary>

Defences (any three): treat retrieved content as data, not instructions (separate it in the prompt); input/document sanitisation and injection detection at ingestion; output guardrails that block requests for card data; least-privilege tools; provenance-based trust levels for sources. Operationally: declare an incident (likely **SEV1**: customer card data at risk), **mitigate** by removing the document from the index and invalidating the semantic cache (or using the kill switch), communicate, then run a blameless postmortem. *(Lessons 5.2, 5.5, 6.5)*

</details>

---
⬅️ [Lesson 6.7 Case studies](07-case-studies.md) · ➡️ [Cheat sheet](cheatsheet.md) · 🏆 [Capstone](../../capstone/README.md)
