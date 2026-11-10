# Module 4 quiz: Evaluation and Monitoring

[Course home](../../README.md) › [Module 4](README.md) › Quiz

15 questions. Answer each one in writing **before** opening the answer. Score 1 point for a fully correct answer, ½ for partly correct. **12+ means you're ready for Module 5**; below that, revisit the lessons linked in the answers you missed. Questions 13–15 review earlier modules.

---

**1.** 2,000 of 100,000 transactions are fraud. A model flags 4,000 transactions and catches 1,500 frauds. Compute precision, recall and accuracy. <!-- id: q-4-1 -->

<details><summary>Answer</summary>

TP = 1,500, FP = 2,500, FN = 500, TN = 100,000 − 1,500 − 2,500 − 500 = 95,500.
Precision = 1,500/4,000 = **0.375**. Recall = 1,500/2,000 = **0.75**. Accuracy = (1,500 + 95,500)/100,000 = **0.97**, *lower* than the 0.98 of "always legit", even though this model catches 75% of fraud. That's why accuracy is the wrong metric here. → [4.1](01-offline-vs-online-and-classification-metrics.md)

</details>

**2.** Why is PR-AUC usually preferred over ROC-AUC for fraud, and what is its value for a random model? <!-- id: q-4-2 -->

<details><summary>Answer</summary>

ROC's FPR has a huge denominator (all negatives), so many false alarms still look like a small FPR; PR shows precision directly. A random model's PR-AUC equals the **base rate** (e.g., 0.02 here), while its ROC-AUC is always 0.5. → [4.1](01-offline-vs-online-and-classification-metrics.md)

</details>

**3.** Review costs €4, a false alarm adds €6 of customer friction, and a missed fraud costs its amount. With calibrated probability p, write the rule to flag a €150 transaction, and give the cut-off. <!-- id: q-4-3 -->

<details><summary>Answer</summary>

Flag if p·150 > 4 + (1 − p)·6 → 156p > 10 → **p > 0.064**. → [4.2](02-thresholds-and-calibration.md)

</details>

**4.** Your model's mean predicted fraud probability is 0.25; the real fraud rate is 0.02. Name the most likely cause and a fix that doesn't change the model's ranking. <!-- id: q-4-4 -->

<details><summary>Answer</summary>

Training with class weighting or resampling (e.g., `class_weight="balanced"`) inflates probabilities. Fix with **Platt scaling or isotonic regression** fitted on held-out data (or `CalibratedClassifierCV(cv=k)`); both are monotone, so ROC-AUC is essentially unchanged. → [4.2](02-thresholds-and-calibration.md)

</details>

**5.** The base rate is 2%. What Brier score does a model need to beat to have any skill? <!-- id: q-4-5 -->

<details><summary>Answer</summary>

The no-skill reference is b(1 − b) = 0.02 × 0.98 = **0.0196**. → [4.2](02-thresholds-and-calibration.md)

</details>

**6.** List the six categories of a good golden set for a RAG assistant, and explain why two of them are "negative". <!-- id: q-4-6 -->

<details><summary>Answer</summary>

Factual, procedural, reasoning, **access-denied**, **unanswerable**, injection probes. Access-denied and unanswerable are negative cases: "good" means refusing or saying "I don't know". Without them, a system that always answers scores perfectly while leaking data and hallucinating. → [4.3](03-evaluating-llm-systems.md)

</details>

**7.** An LLM judge agrees with human labels on 85% of items; humans said "pass" on 85% of items. What do you need to compute, and what might it show? <!-- id: q-4-7 -->

<details><summary>Answer</summary>

**Cohen's kappa** (and the confusion matrix). If the judge always says "pass", agreement = 85% by chance and **kappa ≈ 0**: no ability to detect failures. → [4.3](03-evaluating-llm-systems.md)

</details>

**8.** Give an example of a check that evaluates an agent's trajectory rather than its final answer, and explain why trajectories can be graded without a judge. <!-- id: q-4-8 -->

<details><summary>Answer</summary>

Expected tool `freeze_card` with `card_last4 = "4242"` after the user mentioned the card two turns earlier, or "`freeze_card` must never be called unless the user explicitly asks". Tool calls are structured data (names, arguments, order), so exact comparisons work. → [4.3](03-evaluating-llm-systems.md)

</details>

**9.** Why can't you compute fleet-wide p95 latency by averaging each server's p95? What do you do instead? <!-- id: q-4-9 -->

<details><summary>Answer</summary>

Percentiles aren't additive. Export **histograms**, sum bucket counts across servers, then apply `histogram_quantile(0.95, sum by (le) (rate(..._bucket[5m])))`. → [4.4](04-observability-tracing-and-metrics.md)

</details>

**10.** A teammate adds `labels=["user_id"]` to the request counter "to debug a customer issue". What's the risk, and where should that information go? <!-- id: q-4-10 -->

<details><summary>Answer</summary>

Cardinality explosion: one time series per user can overload Prometheus. Put per-request identifiers on **trace spans or structured logs** instead. → [4.4](04-observability-tracing-and-metrics.md)

</details>

**11.** Recall dropped from 0.49 to 0.31 while every feature's PSI is below 0.1. What kind of drift is this, how did you see it, and what early signal could catch it next time? <!-- id: q-4-11 -->

<details><summary>Answer</summary>

**Concept drift** (P(y|X) changed). It was only visible through **labelled performance**. Earlier signals: fraud found in a random review holdout of unflagged transactions, customer-reported fraud, prediction drift (score distribution), outcome metrics like losses per €1M. → [4.5](05-drift-and-alerting.md)

</details>

**12.** A canary at 5% shows 3 thumbs-down in 40 ratings (7.5%) vs a 2% baseline. Roll back now? Justify with one number. <!-- id: q-4-12 -->

<details><summary>Answer</summary>

Not on this evidence alone: the 95% interval for 3/40 is roughly **2.6%–19.9%**, which overlaps the baseline. Wait for a minimum sample (e.g., 200 ratings) or a longer window, unless an infra or safety gate also fails. → [4.6](06-progressive-delivery-and-prompt-registries.md)

</details>

---

### 🔁 Spaced review (earlier modules)

**13.** 🔁 *(Module 2)* Why is `chargeback_filed` excluded from the fraud model's features, and what would offline metrics look like if it were included? <!-- id: q-4-13 -->

<details><summary>Answer</summary>

It is only known **after** the fraud label exists (target leakage). Including it would make offline metrics look excellent (it is filed for ~85% of fraud) while the model fails live, where the field is not yet available. → [2.2](../02-data-and-model-pipelines/02-lineage-versioning-and-leakage.md)

</details>

**14.** 🔁 *(Module 1)* The `/ready` endpoint in the lab returns the number of chunks and the active prompt version. Why is readiness different from liveness, and why include those details? <!-- id: q-4-14 -->

<details><summary>Answer</summary>

Liveness = "the process is up" (restart if not). Readiness = "I can serve correct traffic now" (stop routing if not): the index must be loaded and a prompt active. Including them lets a deploy or a human see *why* an instance isn't ready. → [1.4](../01-prototype-to-production/04-production-services.md)

</details>

**15.** 🔁 *(Module 3)* The cache hit ratio panel drops from 40% to 5% right after a prompt release. Why might a prompt change cause that, and what are the cost/latency consequences? <!-- id: q-4-15 -->

<details><summary>Answer</summary>

Cache keys include the prompt version (they must, or users would get answers from the old prompt), so a new version starts with a cold cache. Expect higher latency and LLM cost until the cache warms, and factor that into canary cost gates. → [3.5](../03-serving-and-optimization/05-caching-batching-and-autoscaling.md)

</details>

---
⬅️ [Lab 4](lab/README.md) · ➡️ [Cheat sheet](cheatsheet.md)

🚀 **Done?** Tick Module 4 in your progress tracker, then continue to [Module 5: Security and Governance](../05-security-and-governance/README.md).
