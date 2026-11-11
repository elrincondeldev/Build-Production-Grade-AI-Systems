# Module 2 quiz: Data and Model Pipelines

> 15 questions · ~25 min · Answer before opening each one. Questions 13–15 are **spaced review** from earlier modules.

[Course home](../../README.md) › [Module 2](README.md) › Quiz

---

**1.** Your team needs a "number of transactions in the last 10 minutes" feature at scoring time, and a nightly training set. Which ingestion pattern(s)? <!-- id: q-2-1 -->

<details><summary>Answer</summary>

Both: streaming (or near-real-time) computation for the online feature, and batch for the training snapshot, using **one shared feature definition** so training and serving compute the same thing. (Lesson 2.1)

</details>

**2.** An upstream system starts sending amounts in cents. Only 0.44% of rows exceed the €50,000 maximum. Which check catches the incident, and why don't range checks? <!-- id: q-2-2 -->

<details><summary>Answer</summary>

A **dataset-level distribution check** (for example, the median amount must be within an expected range). Most amounts ×100 are still within the per-row range, so row checks see only the few largest purchases. (Lesson 2.1)

</details>

**3.** Row-level vs dataset-level failures: what should a validation gate do with each? <!-- id: q-2-3 -->

<details><summary>Answer</summary>

Row-level: quarantine the bad rows with reasons and continue, unless the bad fraction exceeds a tolerance. Dataset-level (missing columns, duplicate IDs, label rate or volume anomalies, distribution shifts): fail the run and alert. (Lesson 2.1)

</details>

**4.** A new feature lifts PR-AUC from 0.10 to 0.71. Name the first question you ask and two checks you run. <!-- id: q-2-4 -->

<details><summary>Answer</summary>

"When is this value known relative to the prediction?" Checks: the availability contract (is it declared `at_decision`?) and a single-feature score (ROC-AUC near 1 alone is suspicious). Also: compare against domain expectations and check the offline–online gap. (Lesson 2.2)

</details>

**5.** Give three causes of training/serving skew and two ways to prevent it. <!-- id: q-2-5 -->

<details><summary>Answer</summary>

Causes: two implementations of a feature (SQL vs Java), different time windows, different missing-value defaults, stale caches, renamed categories. Prevention: a single shared feature definition or a feature store; logging served features and training on them; preprocessing inside the model artifact; distribution comparisons. (Lesson 2.2)

</details>

**6.** A GPU processes 3,000 samples/s; each CPU worker produces 250 samples/s. How many workers, and what if the machine has 8 cores? <!-- id: q-2-6 -->

<details><summary>Answer</summary>

12 workers plus headroom. With 8 cores you can't get there with workers alone: pre-process deterministic work offline (pre-tokenize, compact formats), reduce per-sample transforms, or move preprocessing to the GPU. (Lesson 2.3)

</details>

**7.** Why does length bucketing reduce padding waste so much more than dynamic padding alone, and what's the risk if you implement it naively? <!-- id: q-2-7 -->

<details><summary>Answer</summary>

With skewed lengths, almost every random batch contains a long sequence, so dynamic padding still pads widely; bucketing groups similar lengths. Naive risk: sorting the whole dataset by length, which makes training order non-random. Bucket within random windows and shuffle the batches. (Lesson 2.3)

</details>

**8.** A partner-uploaded FAQ contains an HTML comment telling "AI assistants" to ask for card numbers. Where in the pipeline do you deal with it first, and is that enough? <!-- id: q-2-8 -->

<details><summary>Answer</summary>

At ingestion: strip hidden content (comments and similar), record provenance, and log a warning. It isn't enough on its own: injections can also be visible text, so Module 5 adds layered defences (input/output guardrails, treating context as data, least privilege). (Lessons 2.4, 5.2)

</details>

**9.** Compute the RRF score (k = 60) of a chunk ranked 3rd by BM25 and 2nd by dense search. <!-- id: q-2-9 -->

<details><summary>Answer</summary>

1/63 + 1/62 ≈ 0.015873 + 0.016129 = **0.032002**. (Lesson 2.5)

</details>

**10.** Why must permission filters run *inside* the search, on *every* retriever? <!-- id: q-2-10 -->

<details><summary>Answer</summary>

Post-filtering can return zero results and has already pulled forbidden content out of the database (into logs, caches, prompts). A filter on only one retriever (for example dense) leaves the other (BM25) leaking. (Lesson 2.5)

</details>

**11.** Increasing Optuna trials from 10 to 30 raised validation PR-AUC (0.102 → 0.128) and lowered test PR-AUC (0.099 → 0.082). What happened, and name two defences. <!-- id: q-2-11 -->

<details><summary>Answer</summary>

Overfitting the validation set: many trials found settings that fit its noise. Defences: an untouched test set used once; (time-aware) cross-validation; confidence intervals before claiming wins; preferring simpler configurations within noise. (Lesson 2.6)

</details>

**12.** Lena wants (a) answers from policies that change monthly and (b) a consistent brand tone. Recommend a technique for each. <!-- id: q-2-12 -->

<details><summary>Answer</summary>

(a) **RAG**: knowledge that changes, needs citations and permissions. (b) **Prompting** with a style guide and a few examples first; a **LoRA** adapter only if prompting proves insufficient or too costly at volume, measured on the same evaluation set. (Lesson 2.7)

</details>

---

### 🔁 Spaced review

**13.** 🔁 *(Module 1)* Why should the model artifact include a sha256 digest and metadata, and how does that connect to this module? <!-- id: q-2-13 -->

<details><summary>Answer</summary>

So the serving service can verify it loaded exactly the artifact that was evaluated, and trace it back to its training run. This module extends the chain upstream: the run links to its data digest, code commit and environment lock, giving end-to-end lineage from raw data to the serving container.

</details>

**14.** 🔁 *(Module 1)* What is the difference between a liveness and a readiness endpoint, and why does the docs-assistant's `/readyz` depend on the index? <!-- id: q-2-14 -->

<details><summary>Answer</summary>

Liveness = "the process is alive" (restart it if not). Readiness = "it can serve traffic now" (don't route requests until it can). The assistant can't answer until the index is built, so `/readyz` returns 503 until then, and load balancers keep traffic away.

</details>

**15.** 🔁 *(Module 0)* Why is accuracy a poor metric for the fraud model, and what does the lab use instead? <!-- id: q-2-15 -->

<details><summary>Answer</summary>

With ~1.3% fraud, predicting "never fraud" scores ~98.7% accuracy and catches nothing. The lab uses PR-AUC (with ROC-AUC as a secondary metric), which focuses on how well the model ranks the rare positive class. Module 4 goes deeper.

</details>

---

**Scoring:** 13–15 → move on · 10–12 → re-read the lessons for the ones you missed · <10 → redo the lab's "Break it" section and retake in two days (spacing helps). <!-- pass: 13 -->

⬅️ [Module 2 overview](README.md) · ➡️ [Cheat sheet](cheatsheet.md)

🚀 **Done?** Tick Module 2 in your progress tracker, then continue to [Module 3: Serving, Inference and Optimization](../03-serving-and-optimization/README.md).
