# Module 0 quiz

> ⏱ ~20 min · Answer each question **before** opening the answer. Score 1 point per question you got substantially right.
> **10+ / 12:** start Module 1. **7–9:** re-read the lessons linked in the answers you missed. **Below 7:** redo the lab steps for those topics, then retake the quiz in a couple of days (the gap helps you remember).

[Course home](../../README.md) › [Module 0](README.md) › Quiz

---

**1.** Your teammate's `pyproject.toml` says `scikit-learn>=1.5` and there is no lock file. CI passed last month and fails today with no code changes. What's the most likely cause, and the fix? <!-- id: q-0-1 -->

<details><summary>Answer</summary>

A newer version of a dependency (direct or transitive) was resolved today and changed behaviour. Fix: commit a **lock file** (`uv.lock`) so every install gets exact, hashed versions; upgrade deliberately with `uv lock --upgrade` in its own reviewed change. → [Lesson 0.2](02-python-for-production.md)

</details>

**2.** Which of these should be validated with Pydantic, and which can be plain dataclasses? (a) the JSON body of `POST /score`, (b) a `Metrics` object your own evaluation function returns, (c) environment variables, (d) the JSON an LLM returns when asked for structured output. <!-- id: q-0-2 -->

<details><summary>Answer</summary>

**Pydantic:** (a), (c) and (d), because all of them cross a trust boundary (clients, the environment, a model that can return anything). **Dataclass:** (b), internal data your own code created. Rule: validate at the edges, trust inside. → [Lesson 0.2](02-python-for-production.md)

</details>

**3.** An `async def` endpoint calls `time.sleep(2)` to "wait for a lock". Under load, latency for *all* endpoints jumps. Why? <!-- id: q-0-3 -->

<details><summary>Answer</summary>

`time.sleep` **blocks the event loop**: while it sleeps, no other request on that worker can make progress. Use `await asyncio.sleep(...)` (or async primitives), and move unavoidable blocking work to a thread or process pool. → [Lesson 0.2](02-python-for-production.md)

</details>

**4.** Match each status code to the right action: `422`, `429`, `503`, `403`. <!-- id: q-0-4 -->

<details><summary>Answer</summary>

- **422**: the client fixes the request body (validation failed). No retry.
- **429**: rate limited, so wait (respect `Retry-After`) and retry with backoff; investigate quotas if sustained.
- **503**: the service is overloaded or unavailable, so retry with backoff; the service owner investigates.
- **403**: the caller is authenticated but not allowed. No retry; needs a different permission.

→ [Lesson 0.3](03-http-and-apis.md)

</details>

**5.** Why is it dangerous to automatically retry `POST /payments` after a timeout, and what's the standard fix? <!-- id: q-0-5 -->

<details><summary>Answer</summary>

The first request may have **succeeded** with only the response lost, so a retry can charge twice. Fix: an **idempotency key** sent by the client and deduplicated by the server, which returns the stored result for repeats. → [Lesson 0.3](03-http-and-apis.md)

</details>

**6.** Kestrel's test set has 10,000 transactions with 141 frauds. A model flags 30 transactions, 20 of which are fraud. Compute precision, recall and accuracy. <!-- id: q-0-6 -->

<details><summary>Answer</summary>

TP = 20, FP = 10, FN = 141 − 20 = 121, TN = 10,000 − 141 − 10 = 9,849.
**Precision** = 20 / 30 = **66.7%**. **Recall** = 20 / 141 = **14.2%**. **Accuracy** = (20 + 9,849) / 10,000 = **98.69%**, barely above the 98.59% of "always not fraud". → [Lesson 0.4](04-ml-in-one-hour.md)

</details>

**7.** Omar says "missing a fraud costs us far more than a false alarm." Should the threshold go up or down from 0.5? What will happen to precision and recall? <!-- id: q-0-7 -->

<details><summary>Answer</summary>

**Down.** More transactions get flagged, so **recall rises** and **precision usually falls** (more false alarms). The exact threshold should come from the costs of each error type (Module 4). → [Lesson 0.4](04-ml-in-one-hour.md)

</details>

**8.** A model gets 100% recall on training data and 7% on test data. Name the problem and one fix that does *not* involve collecting more data. <!-- id: q-0-8 -->

<details><summary>Answer</summary>

**Overfitting.** Fixes: reduce model complexity (limit tree depth, minimum samples per leaf, regularisation), use ensembles with early stopping, choose hyperparameters on a validation set. → [Lesson 0.4](04-ml-in-one-hour.md)

</details>

**9.** For each candidate feature of a real-time fraud model, say *use* or *leak*: (a) `txn_count_24h` computed from transactions *before* this one, (b) `chargeback_filed`, (c) `analyst_review_outcome`, (d) `device_is_new`. <!-- id: q-0-9 -->

<details><summary>Answer</summary>

(a) **Use**, since it's known at scoring time *if* computed only from the past. (b) **Leak**, filed after the fact. (c) **Leak**, it's essentially the label. (d) **Use**, known when the transaction arrives. The test: *would I know this value at the moment the prediction is needed?* → [Lesson 0.4](04-ml-in-one-hour.md)

</details>

**10.** True or false, and why: "Setting temperature to 0 prevents hallucinations." <!-- id: q-0-10 -->

<details><summary>Answer</summary>

**False.** Temperature 0 picks the most likely token each step, which reduces *randomness*, not *falsehood*. If the model lacks the fact, the most likely continuation can still be wrong, delivered consistently. Grounding (RAG), citations and evaluations address correctness. → [Lesson 0.5](05-llms-in-one-hour.md)

</details>

**11.** Hash embeddings rank "How do partners get support?" first for the query "Can I get my money back for a fee?". Explain why, and name the kind of retrieval that combines the strengths of both approaches. <!-- id: q-0-11 -->

<details><summary>Answer</summary>

Hash embeddings capture **shared words** (here, "get") rather than meaning, plus random hash collisions. Semantic embeddings capture paraphrases but can blur exact identifiers. **Hybrid retrieval** combines lexical (e.g. BM25) and semantic (dense vector) search, usually followed by reranking (Lesson 2.5). → [Lesson 0.5](05-llms-in-one-hour.md)

</details>

**12.** A RAG answer uses 2,000 input tokens and 300 output tokens. With illustrative prices of $2.50 per 1M input tokens and $10.00 per 1M output tokens, what does one call cost, and what do 1M calls cost? Name two ways to cut it. <!-- id: q-0-12 -->

<details><summary>Answer</summary>

Input: 2,000 / 1,000,000 × $2.50 = $0.005. Output: 300 / 1,000,000 × $10.00 = $0.003. **$0.008 per call, about $8,000 per 1M calls.** Cut it by retrieving fewer and tighter chunks, shortening prompts, routing easy questions to a smaller model, caching repeated questions, or capping answer length. → [Lesson 0.5](05-llms-in-one-hour.md)

</details>

---

### 🔁 Spaced review

There are no earlier modules yet. Starting in Module 1, every quiz ends with questions from previous modules. **Put a reminder in your calendar to retake this quiz one week from now**: retrieving answers after a gap is one of the most effective ways to make them stick.

---
⬅️ [Lab 0](lab/README.md) · ➡️ [Cheat sheet](cheatsheet.md) · ⏭️ [Module 1](../01-prototype-to-production/README.md)
