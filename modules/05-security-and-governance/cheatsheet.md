# Module 5 cheat sheet: Security and Governance

[Course home](../../README.md) › [Module 5](README.md) › Cheat sheet

## Mental model

> LLMs mix **instructions and data in one channel**. Assume the model can be fooled. Control what goes **in**, check what comes **out**, and limit what it can **do**.

## OWASP Top 10 for LLM Applications (2025)

| | Risk | One-line mitigation |
|---|---|---|
| LLM01 | Prompt Injection | Layers: sanitise + provenance → detect (inputs *and* chunks) → delimit → output checks → least privilege |
| LLM02 | Sensitive Information Disclosure | Authorize before retrieval; redact; minimise data |
| LLM03 | Supply Chain | Pin and hash dependencies, trusted model sources, `safetensors` |
| LLM04 | Data and Model Poisoning | Provenance, review corpus changes, ingest anomaly checks |
| LLM05 | Improper Output Handling | Schema-validate, escape, never `eval`/`innerHTML` model output |
| LLM06 | Excessive Agency | Minimal tools and permissions; human approval for risky actions |
| LLM07 | System Prompt Leakage | No secrets in prompts; n-gram leak detection |
| LLM08 | Vector and Embedding Weaknesses | Access metadata on every chunk; filter in the DB; embeddings are sensitive |
| LLM09 | Misinformation | Grounding, citations, abstention, evals |
| LLM10 | Unbounded Consumption | Auth + per-identity rate/size/token limits + budget alarms |

## Threat model in one page

Assets · Actors · Entry points (diagram) · **STRIDE** (Spoofing, Tampering, Repudiation, Information disclosure, DoS, Elevation of privilege) · Likelihood × Impact · Mitigation → test.

## Auth

- 401 = who are you? · 403 = not allowed (for *data*, answer like "not found")
- JWT = signed, **not encrypted**. Validate signature, `exp`, `iss`, `aud`, required claims. **Pin the algorithm.**
- Short-lived tokens; deny unknown roles; no insecure defaults in prod.

## Permission-aware RAG

```
✅ filter(role) → rank → top-k → prompt          ❌ rank(all) → top-k → filter → prompt
```

Stats (IDF) per partition · cache key includes permissions · deletions propagate to index **and** caches · never "enforce" access in the prompt.

## PII

Map flows: prompt · logs · traces · audit · cache · eval sets · backups.
Prefer: don't collect → redact at edge → pseudonymise/tokenise → encrypt.
Cards: regex + **Luhn** · IBAN: regex + **mod-97** · names: NER (Presidio). Logs → optimise **recall**.
`sha256(email)` ≠ anonymous; use HMAC with a KMS key, still personal data.

## Encryption

In transit: TLS 1.2+ (prefer 1.3), HSTS, mTLS between services.
At rest: disk < DB/bucket < field-level. **Envelope**: DEK encrypts data, KMS KEK wraps DEK. Delete key = crypto-shred.

## Guardrail pipeline (lab order)

1 input guard → 2 role pre-filtered retrieval → 3 chunk quarantine → 4 trust-labelled prompt → LLM → 5 **output contract** → 6 content guards (credentials, prompt leak) → 7 citations ⊆ retrieved + **groundedness** → 8 PII redaction → 9 **audit**.
Cheap first · decide fail-open/closed per check · every refusal has a **reason code** · track **over-refusal**.

## Groundedness

| Lexical | NLI | LLM judge |
|---|---|---|
| < 1 ms, free, misses meaning | 10–100 ms, good on short claims | 0.5–3 s, flexible, needs calibration |

Grounded ≠ correct ≠ safe.

## Audit log

Who, what (redacted), why (retrieved ids, policy version, reason), when, cost. `hash_n = sha256(record_n incl. prev_hash)`. Detects edits and deletions; **not** truncation or full rewrites → anchor externally + WORM storage.

## Governance

- **Model card**: intended use, **out of scope**, data, metrics, **fairness**, explainability, risks, change log. **Datasheet** for corpora.
- **Fairness**: start from harms → FPR/TPR by group **and proxy** → base rates differ ⇒ can't equalise everything → decide, document, assign an owner.
- **Explain**: coefficients/SHAP for tabular; **citations = provenance** for RAG.
- **EU AI Act** (classification follows *use*): prohibited · **high-risk** (Annex III, incl. credit scoring; *fraud detection excluded*) · transparency (chatbots disclose AI) · minimal. Not legal advice.
- **NIST AI RMF**: Govern · Map · Measure · Manage. **AI 600-1** GenAI risks: confabulation, privacy, info security, bias, value chain, …

## Prompt/policy registry

Immutable **bundle** = prompt + thresholds + limits. Author (PR) → **four-eyes** → offline checks (clauses + golden eval vs worst-case model; security gates at **100%**) → audited activate → canary → fast audited **rollback** (no checks). Record `policy_version` on every answer. *Can your eval see the change?*

## Lab commands

```bash
uv run pytest -q
uv run python scripts/ask.py --role customer --show-prompt "question"
uv run python scripts/issue_token.py --sub alice --role customer
uv run python scripts/verify_audit_log.py
uv run python scripts/registry_cli.py list | check V | activate V --actor you | rollback --actor you
uv run --extra governance python scripts/fairness_audit.py
```

---
⬅️ [Quiz](quiz.md) · [Module 5 overview](README.md)
