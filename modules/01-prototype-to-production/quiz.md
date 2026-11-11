# Module 1 quiz: From Prototype to Production

[Course home](../../README.md) › [Module 1](README.md) › Quiz

> 14 questions · ~25 min · Answer each one **before** opening the solution. Score 1 point per question; aim for **11+ (80%)**.
> Questions 12–14 are **spaced review** from Module 0: they're here on purpose, because retrieving older material is what makes it stick.

---

**1.** *Leakage detective.* A churn model's ROC-AUC jumps from 0.72 to 0.94 after adding `days_since_last_support_ticket_closed`. Tickets are often closed *as part of* the cancellation process. What do you suspect, and what single question settles it? <!-- id: q-1-1 -->

<details><summary>Answer</summary>

**Label leakage.** The feature is partly caused by the outcome (cancellation closes tickets). The settling question: *"At the moment we make this prediction in production, does this value exist, with the same meaning?"* If it's only known during/after churn, it can't be used. (Lesson 1.1)

</details>

**2.** *Skew in the wild.* Training computes `avg_amount_30d` from a complete nightly warehouse table. Serving computes it from a Redis cache that only holds the last 7 days for new customers. Which kind of training/serving skew is this, and name two fixes. <!-- id: q-1-2 -->

<details><summary>Answer</summary>

**Different data sources/freshness** between offline and online. Fixes: compute the feature once in a feature store that serves both offline (point-in-time-correct) and online values; log served feature values and train on them; add monitoring comparing online vs offline feature distributions. (Lessons 1.1, 1.2)

</details>

**3.** *Inference mode.* Pick batch, online or streaming for each, with a one-line reason: (a) re-score all 2 million accounts for quarterly risk review; (b) decide whether to approve a card payment; (c) flag suspicious login patterns within 30 seconds for the security team's dashboard. <!-- id: q-1-3 -->

<details><summary>Answer</summary>

(a) **Batch**: nobody waits; cheapest at volume. (b) **Online**: the payment is blocked waiting for a decision using request-time data. (c) **Streaming**: fresh within seconds, but nobody's request is blocked. (Lesson 1.2)

</details>

**4.** *Latency budget.* The payments team gives fraud-service 100 ms at p99. Network + gateway take 15 ms, the feature store p99 is 35 ms, the model 4 ms, logging 1 ms. Can you afford one retry of the feature store call? Show your arithmetic. <!-- id: q-1-4 -->

<details><summary>Answer</summary>

Base path: 15 + 35 + 4 + 1 = **55 ms**, leaving 45 ms. A retry costs another up to 35 ms plus backoff (say 0–10 ms with jitter): ~45 ms worst case. It **just fits with no margin**. In practice: set a tighter per-attempt timeout (e.g. 25 ms) so that timeout + backoff + retry stays well under 45 ms, and enforce an overall deadline. (Lessons 1.2, 1.3)

</details>

**5.** *What to retry.* For each, retry or not: (a) `GET /features` → timeout; (b) `GET /features` → 404; (c) `POST /refunds` → connection reset, no idempotency key; (d) `GET /features` → 429 with `Retry-After: 1`. <!-- id: q-1-5 -->

<details><summary>Answer</summary>

(a) **Yes** (idempotent, transient). (b) **No** (the request is wrong or the resource doesn't exist). (c) **No**: the refund may already have been applied; add an idempotency key first. (d) **Yes, after at least 1 s** (if your deadline allows). (Lesson 1.3)

</details>

**6.** *Retry amplification.* Four services in a chain each make up to 3 attempts. The last one is down. How many requests reach it for one user action, and what are two defences? <!-- id: q-1-6 -->

<details><summary>Answer</summary>

3 retrying layers above it (if the user-facing call also retries, it's 4): 3³ = **27** (or 3⁴ = 81). Defences: retry at only one layer; retry budgets; deadlines; circuit breakers; cap attempts at 2–3. (Lesson 1.3)

</details>

**7.** *Jitter.* Explain in two sentences why `sleep = base × 2^n` alone is dangerous when thousands of clients fail at the same moment, and what full jitter changes. <!-- id: q-1-7 -->

<details><summary>Answer</summary>

All clients compute the same delays, so their retries arrive in synchronized waves (a thundering herd) that can knock over a recovering service. Full jitter picks a random delay in `[0, cap]`, spreading retries evenly over the window. (Lesson 1.3)

</details>

**8.** *Fail open or closed?* fraud-service is completely unreachable. Who decides whether payments are approved or declined, and what should the decision depend on? <!-- id: q-1-8 -->

<details><summary>Answer</summary>

The **business** (Risk/Omar), agreed in advance and implemented in the caller. It depends on the relative cost of errors: blocking legitimate customers vs letting fraud through, often split by amount or risk tier (e.g. approve under €50, review above). Engineering implements and tests the policy. (Lesson 1.3)

</details>

**9.** *Layers.* In which layer (API, domain, adapters) does each belong: (a) converting `hour: 25` into a 422 response; (b) the rule "decline if score ≥ 0.8"; (c) the httpx client with retries for the feature store; (d) `build_feature_vector`. <!-- id: q-1-9 -->

<details><summary>Answer</summary>

(a) **API** (schema validation). (b) **Domain** (`DecisionPolicy`). (c) **Adapters** (`HttpFeatureStore`). (d) **Domain** (`features.py`, shared by training and serving). (Lesson 1.4)

</details>

**10.** *Blocking the loop.* An `async def` endpoint does `df = pd.read_csv("big.csv")` (3 s of CPU and disk) on every request. Under load, `/health` times out and Kubernetes restarts the pod. Explain the chain of events and give two fixes. <!-- id: q-1-10 -->

<details><summary>Answer</summary>

The blocking call holds the single event-loop thread for 3 s, so no other coroutine runs, including `/health`. Liveness probes time out → Kubernetes kills the pod → capacity drops further. Fixes: do the heavy work once at startup (lifespan) or in batch; run it in a thread/process pool (`run_in_threadpool`, `asyncio.to_thread`); make the endpoint a plain `def` so FastAPI uses a thread pool. (Lesson 1.4)

</details>

**11.** *Artifacts and containers.* (a) What does a matching sha256 prove, and what doesn't it prove? (b) Why does Lab 1's Dockerfile copy `pyproject.toml` and `uv.lock` before `src/`? <!-- id: q-1-11 -->

<details><summary>Answer</summary>

(a) It proves the file is byte-for-byte the one recorded in the metadata (not corrupted or swapped *without* updating the metadata). It does **not** prove who produced it (needs a signature) or that the model is good (needs evaluation). (b) Layer caching: dependencies change rarely, so their install layer stays cached and code-only changes rebuild in seconds. (Lesson 1.5)

</details>

---

### 🔁 Spaced review (Module 0)

**12.** 🔁 *(Module 0)* *HTTP status codes.* What's the difference between a 4xx and a 5xx status code, and which family is usually worth retrying? <!-- id: q-1-12 -->

<details><summary>Answer</summary>

**4xx**: the client's request is wrong (bad input, unauthorized, not found). **5xx**: the server failed to handle a valid request. 5xx (plus 429, which is technically 4xx but means "slow down") are usually worth retrying; other 4xx are not. ([Lesson 0.3](../00-foundations/03-http-and-apis.md))

</details>

**13.** 🔁 *(Module 0)* *Accuracy on imbalanced data.* Why is 99% accuracy unimpressive for fraud detection with a 1.4% fraud rate? <!-- id: q-1-13 -->

<details><summary>Answer</summary>

A trivial model that always predicts "not fraud" gets 98.6% accuracy while catching zero fraud. Accuracy is dominated by the majority class; you need precision, recall and PR-AUC (Module 4). ([Lesson 0.4](../00-foundations/04-ml-in-one-hour.md))

</details>

**14.** 🔁 *(Module 0)* *Tokens and latency.* Why does an LLM's total response time grow with the length of the answer, and how does streaming change the *user's* experience without changing total time? <!-- id: q-1-14 -->

<details><summary>Answer</summary>

LLMs generate output **one token at a time**, so more output tokens means more sequential generation steps. Streaming sends each token as it's generated, so the user sees text after the time to first token instead of waiting for the whole answer. ([Lesson 0.5](../00-foundations/05-llms-in-one-hour.md))

</details>

---

**Score:** ___ / 14 · Under 11? Revisit the lessons named in the answers you missed, then retake the quiz in two days (spacing works). <!-- pass: 11 -->

⬅️ [Module 1 overview](README.md) · 📄 [Cheat sheet](cheatsheet.md)

🚀 **Done?** Tick Module 1 in your progress tracker, then continue to [Module 2: Data and Model Pipelines](../02-data-and-model-pipelines/README.md).
