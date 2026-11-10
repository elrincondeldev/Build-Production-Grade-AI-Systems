# Module 3 quiz: Serving, Inference and Optimization

[Course home](../../README.md) › [Module 3](README.md) › Quiz

14 questions. Answer each one in writing **before** opening the solution; retrieval practice only works if you commit to an answer. Aim for 11/14. Questions marked 🔁 are spaced review from earlier modules.

---

**1.** An app service runs 6 replicas, and each loads the same 8 GB model in-process. Give two concrete problems and the architectural fix. <!-- id: q-3-1 -->

<details><summary>Answer</summary>

Problems: 6× the model memory (48 GB) and cost; every API deploy reloads the weights (slow, risky deploys); no batching across replicas; scaling the API forces scaling the model. Fix: a dedicated inference service (model server with batching) that all app replicas call over HTTP/gRPC. Lesson 3.1.

</details>

---

**2.** For a decode step with batch size *B*, what's the approximate arithmetic intensity, and what does it imply for a GPU with a ridge point of ~300 FLOPs/byte? <!-- id: q-3-2 -->

<details><summary>Answer</summary>

≈ B FLOPs/byte (2·B·d² FLOPs over ~2·d² bytes of weights). At small B, decode is deeply memory-bound, so increasing the batch raises throughput almost linearly until roughly B ≈ 300 or memory runs out. Lesson 3.2.

</details>

---

**3.** A 14B-parameter model runs in BF16 on a GPU with ~2 TB/s memory bandwidth. What's the best possible single-stream decode speed? What happens with INT4 weights? <!-- id: q-3-3 -->

<details><summary>Answer</summary>

BF16: 28 GB ÷ 2,000 GB/s = 14 ms/token, so ≤ ~71 tokens/s. INT4 (~7 GB plus scales, say ~8 GB): ~4 ms/token, so ≤ ~250 tokens/s as an upper bound. Real numbers are lower, and the gain is in decode (memory-bound), not prefill. Lessons 3.2 and 3.6.

</details>

---

**4.** A model has 48 layers, 8 KV heads and head dimension 128, with a BF16 KV cache. How much KV memory does one 16,000-token sequence need? How many such sequences fit in 40 GB of free KV memory? <!-- id: q-3-4 -->

<details><summary>Answer</summary>

Per token: 2 × 48 × 8 × 128 × 2 = 196,608 bytes = 192 KiB. Per sequence: 16,000 × 192 KiB = 3,072,000 KiB ≈ 2.93 GiB. 40 GB ≈ 37.25 GiB, so ~12 sequences. Lesson 3.2.

</details>

---

**5.** Your small model costs $0.20 per 1,000 requests and the large one $2.00. What escalation rate makes a small→large cascade break even on cost? What else must you measure? <!-- id: q-3-5 -->

<details><summary>Answer</summary>

Break-even when 0.20 + p × 2.00 = 2.00, so p = 0.9 (90%). Below 90% escalation the cascade is cheaper. You must also measure end-to-end quality on the golden set (is the escalation signal reliable?) and the latency of escalated requests, which pay both models' TTFT. Lesson 3.3.

</details>

---

**6.** Load test results: c=2 → 4 req/s, p50 500 ms; c=8 → 10 req/s, p50 800 ms; c=32 → 10 req/s, p50 3.2 s. Where is the knee, and does Little's law agree with the c=32 row? <!-- id: q-3-6 -->

<details><summary>Answer</summary>

The knee is around c=8: throughput plateaus at ~10 req/s and extra concurrency only adds waiting. Little's law: W = L/λ = 32/10 = 3.2 s, which matches. Lesson 3.4.

</details>

---

**7.** Why can a closed-loop load generator report a better p99 than users actually experience during a stall? <!-- id: q-3-7 -->

<details><summary>Answer</summary>

Coordinated omission: closed-loop clients wait for responses before sending more, so during a stall they stop sending, and the requests that would have arrived and queued are never measured. Use open-loop (fixed arrival rate) testing for tail latency. Lesson 3.4.

</details>

---

**8.** A semantic cache serves "What's the ATM fee on Basic?" with the cached answer for "What's the ATM fee on Plus?". Name the bug class, and two fixes. <!-- id: q-3-8 -->

<details><summary>Answer</summary>

A false hit: high embedding similarity, different meaning. Fixes: raise the threshold, tuned on labelled hard-negative pairs for hit precision; restrict semantic caching to curated low-risk intents; add entity-aware checks (the plan name must match); sample and review hits; or use exact caching only for fee questions. Lesson 3.5.

</details>

---

**9.** Explain in two sentences why continuous batching achieves much lower TTFT than static batching under load. <!-- id: q-3-9 -->

<details><summary>Answer</summary>

With static batching a new request must wait until the whole running batch, including its longest generation, finishes. Continuous batching re-forms the batch at every decode step, so a waiting request is admitted (prefilled) at the next step as soon as any slot frees up. Lesson 3.5.

</details>

---

**10.** Which autoscaling signal would you use for a vLLM deployment, and why not GPU utilization? <!-- id: q-3-10 -->

<details><summary>Answer</summary>

Queue depth (waiting requests) and KV-cache usage, with TTFT p95 as a secondary signal. GPU "utilization" only says a kernel was running, not how much capacity is used. With continuous batching it can sit near 100% at both moderate and overloaded traffic. Lesson 3.5.

</details>

---

**11.** You apply weight-only INT4 quantization. TPOT improves a lot, but TTFT for long RAG prompts barely changes. Explain. <!-- id: q-3-11 -->

<details><summary>Answer</summary>

Weight-only quantization reduces bytes read per decode step (decode is memory-bound, so TPOT improves) but the matmuls still run in 16-bit after dequantization. Prefill is compute-bound, so its FLOPs and TTFT barely change. W8A8/FP8 or shorter prompts and prefix caching would help TTFT. Lessons 3.2 and 3.6.

</details>

---

**12.** 🔁 *(Module 1)* The ONNX fraud service encodes `merchant_category` with a different column order than training did. Nothing crashes. What is this called, and how does lesson 3.7's packaging prevent it? <!-- id: q-3-12 -->

<details><summary>Answer</summary>

Training/serving skew: the model receives features that differ from what it was trained on, producing silently wrong scores. Prevention: one shared encoding function used by training and serving, artifact metadata listing feature order and IO names, a startup check that refuses readiness on mismatch, and a parity gate in CI. Lessons 1.1 and 3.7.

</details>

---

**13.** 🔁 *(Module 1)* Your fallback chain retries the primary LLM on every error, immediately, 5 times. Name two problems and the correct policy. <!-- id: q-3-13 -->

<details><summary>Answer</summary>

Immediate retries amplify load during an outage (retry storms), and retrying non-retryable errors (400 validation errors) is pointless, while users wait through 5 failures before the fallback. Correct: retry only retryable errors (timeouts, 429, 503) with exponential backoff + jitter and a retry budget, honour Retry-After, use a circuit breaker to fail over quickly, and set timeouts from the latency budget. Lessons 1.3 and 3.3.

</details>

---

**14.** 🔁 *(Module 2)* Retrieval returns 20 chunks "to be safe", making prompts 4,000 tokens. Name three serving consequences and one Module 2 technique that lets you send fewer chunks. <!-- id: q-3-14 -->

<details><summary>Answer</summary>

Higher TTFT (more prefill), more KV memory per request (fewer concurrent sequences, so lower throughput), and higher input-token cost. Lost-in-the-middle quality effects are another. Module 2 fix: hybrid retrieval with reranking, so the top 3–5 chunks are the right ones (plus context packaging with token caps). Lessons 2.5, 3.2 and 3.3.

</details>

---

**Score yourself:** 12–14 → move on to Module 4. 9–11 → reread the lessons for the questions you missed. ≤ 8 → redo lab steps 1, 3 and 5, then retake the quiz in two days.

⬅️ [Module 3 overview](README.md) · 📄 [Cheat sheet](cheatsheet.md)

🚀 **Done?** Tick Module 3 in your progress tracker, then continue to [Module 4: Evaluation and Monitoring](../04-evaluation-and-monitoring/README.md).
