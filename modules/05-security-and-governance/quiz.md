# Module 5 quiz: Security and Governance

[Course home](../../README.md) › [Module 5](README.md) › Quiz

Answer each question **before** opening the answer. Write your answers down: retrieval practice only works if you actually retrieve. Questions marked 🔁 review earlier modules.

Scoring: 12–14 correct, move on. 9–11, re-read the lessons for the ones you missed. Fewer than 9, redo the lab's Break-it section first.

---

**1.** Map each scenario to its OWASP LLM Top 10 (2025) entry: <!-- id: q-5-1 -->
(a) the support UI renders the assistant's answer as HTML and a `<script>` tag runs;
(b) a script sends 800,000 long questions in a day;
(c) an agent with a `create_refund` tool issues refunds because a document said so;
(d) a customer gets salary-band information.

<details><summary>Answer</summary>

(a) **LLM05** Improper Output Handling; (b) **LLM10** Unbounded Consumption; (c) **LLM06** Excessive Agency (triggered by LLM01 Prompt Injection); (d) **LLM02** Sensitive Information Disclosure (often caused by **LLM08** Vector and Embedding Weaknesses, i.e. missing access metadata or filters).

</details>

---

**2.** Why is indirect prompt injection generally more dangerous than direct prompt injection? <!-- id: q-5-2 -->

<details><summary>Answer</summary>

The direct attacker only affects their own session. An indirect payload, planted once in content the system retrieves, hits **every** user whose request retrieves it, and arrives with the assistant's credibility (even a citation). The victims never see the payload.

</details>

---

**3.** The lab sanitises documents *before* chunking. What specific failure does that order prevent? <!-- id: q-5-3 -->

<details><summary>Answer</summary>

A hidden block (e.g. an HTML comment) split across two chunks. Each half no longer matches the comment pattern, so the payload would survive in pieces. Sanitising the whole document first removes it entirely.

</details>

---

**4.** Compute the noisy-OR injection score for a text that matches patterns with weights 0.6 and 0.5 only. Is it quarantined at a threshold of 0.7? <!-- id: q-5-4 -->

<details><summary>Answer</summary>

`1 − (1−0.6)(1−0.5) = 1 − 0.4 × 0.5 = 0.8`. Yes: 0.8 ≥ 0.7, so it's quarantined.

</details>

---

**5.** A colleague writes `jwt.decode(token, key, algorithms=jwt.get_unverified_header(token)["alg"])`. What's the vulnerability and the fix? <!-- id: q-5-5 -->

<details><summary>Answer</summary>

The token chooses its own algorithm, which enables `alg: none` tokens and RS256→HS256 key confusion. Fix: pin the expected algorithm(s) in code, e.g. `algorithms=["HS256"]` (or `["RS256"]`), and require `exp`, `iss`, `aud` and your custom claims.

</details>

---

**6.** Give three reasons post-filtering retrieval results (rank everything, drop forbidden chunks after) is worse than pre-filtering, even if the filter is correct. <!-- id: q-5-6 -->

<details><summary>Answer</summary>

(1) Result counts, quality and latency depend on forbidden content: a side channel. (2) Any code path that forgets the filter (cache, debug endpoint, "related docs") leaks directly. (3) Users with less access get fewer, worse chunks (lower recall). Bonus: corpus statistics like IDF reflect forbidden documents unless computed per partition.

</details>

---

**7.** Kestrel's logs have 1,000,000 lines/day; 2% contain an email. A redactor has 98% recall and 90% precision. How many emails leak per day, and which number should you improve first for logs? <!-- id: q-5-7 -->

<details><summary>Answer</summary>

20,000 emails × 2% missed = **400 leaked per day**. For logs, improve **recall** first: a miss is a leak, while a false positive only makes a log line less useful.

</details>

---

**8.** Explain envelope encryption in three steps, and say what "crypto-shredding" means. <!-- id: q-5-8 -->

<details><summary>Answer</summary>

(1) Encrypt the data locally with a random data key (DEK). (2) Encrypt the DEK with a master key (KEK) held in a KMS; store the encrypted DEK with the ciphertext. (3) To decrypt, ask the KMS (permission-checked, logged) to unwrap the DEK. **Crypto-shredding**: deleting the key makes every copy of the data unreadable, including immutable backups.

</details>

---

**9.** An answer scores 1.0 on the lab's lexical groundedness check but is factually wrong. How is that possible, and what would catch it? <!-- id: q-5-9 -->

<details><summary>Answer</summary>

Lexical overlap only checks that the answer's words appear in the sources, not how they relate. "Card replacement is free on all plans" reuses words from a sentence that says it costs €7 on Basic. An NLI (entailment) model or a calibrated LLM judge that reads the claim against the source would flag the contradiction.

</details>

---

**10.** The hash-chained audit log verifies as intact. Name two ways an attacker with write access could still have altered history, and the mitigation for each. <!-- id: q-5-10 -->

<details><summary>Answer</summary>

(1) Truncating the most recent records: mitigate by periodically anchoring the latest hash in a separate system. (2) Rewriting the whole file and recomputing all hashes: mitigate with write-once (WORM/object-lock) storage or shipping records to a system the service can't modify.

</details>

---

**11.** In the fraud fairness audit, legitimate customers abroad have an FPR of 20.9% vs 0.2% at home, while fraud rates are 7.4% vs 1.1%. Why can't you simply "equalise everything"? What do you do instead? <!-- id: q-5-11 -->

<details><summary>Answer</summary>

When base rates differ, a non-perfect classifier can't be calibrated within each group and have equal FPR and FNR across groups at the same time (the fairness impossibility result), so you must choose which property matters. Instead: start from harms (blocked legitimate payments), improve features and model, change the *action* (step-up auth instead of decline), consider segment thresholds only with legal review, and document the decision and its owner in the model card.

</details>

---

**12.** Under the EU AI Act, what's the likely starting classification of (a) the fraud model, (b) the docs-assistant, (c) a model that sets customers' credit limits? (Remember: confirm with Legal.) <!-- id: q-5-12 -->

<details><summary>Answer</summary>

(a) Not high-risk under the creditworthiness use case, because Annex III explicitly excludes AI used to detect financial fraud (GDPR and other laws still apply). (b) Limited risk: transparency obligation to tell users they're interacting with AI. (c) High-risk: Annex III, creditworthiness and credit scoring of natural persons.

</details>

---

**13.** 🔁 *(Module 4, progressive delivery)* Bundle 1.1.0 is activated for 5% of traffic as a canary. Which three signals from this module would you watch before going to 100%? <!-- id: q-5-13 -->

<details><summary>Answer</summary>

For example: refusal rate by reason code (`ungrounded`, `contract_violation`, `model_abstained`) compared with the control group; groundedness score distribution; `input_blocked:prompt_injection` and `output_blocked:*` rates; user feedback/escalation rate; cost per answer. Roll back automatically if over-refusal or contract violations spike.

</details>

---

**14.** 🔁 *(Module 2, retrieval; Module 3, caching)* You add a semantic cache in front of the docs-assistant to save cost. What must the cache key include, and what must happen when a document is deleted? <!-- id: q-5-14 -->

<details><summary>Answer</summary>

The key must include the user's **permission set** (role/tenant), not just the question embedding. Otherwise an HR user's cached salary answer can be served to a customer. On deletion, invalidate every cached answer that cited the document (store `doc_id`s with each cache entry), in addition to removing its chunks from the index.

</details>

---
⬅️ [Module 5 overview](README.md) · 📄 [Cheat sheet](cheatsheet.md)

🚀 **Done?** Tick Module 5 in your progress tracker, then continue to [Module 6: Scaling and Operations](../06-scaling-and-operations/README.md).
