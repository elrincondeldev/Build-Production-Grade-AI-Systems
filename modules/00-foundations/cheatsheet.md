# Module 0 cheat sheet: Foundations

[Course home](../../README.md) › [Module 0](README.md) › Cheat sheet

## 🧰 Toolchain

| Tool | Solves | Key commands |
|---|---|---|
| **uv** | Exact Python + packages | `uv sync` · `uv run <cmd>` · `uv add <pkg>` · `uv lock --upgrade` |
| **Git** | History, review, rollback | `git switch -c <branch>` · `git add -A && git commit -m "..."` · `git pull upstream main` |
| **Docker** | Ship the whole runtime | `docker build -t name .` · `docker run --rm -p 8000:8000 name` |
| **Ollama** | Free local LLMs | `ollama pull qwen2.5:1.5b-instruct` · `ollama run <model> "prompt"` · API on `:11434` |

Commit `pyproject.toml` + `uv.lock`. Never commit `.venv/`, `.env`, data or model artifacts.

## 🐍 Python for production

- **Validate at the edges** (Pydantic: HTTP bodies, config, files, LLM output); **trust inside** (dataclasses).
- **Config from env**: `KESTREL_*` via `pydantic-settings`; secrets as `SecretStr`; fail fast on bad config.
- **Testable = injectable**: pass clients and transports in; fake the network (`httpx.MockTransport`), not the logic.
- **Log, don't print.** Levels, timestamps, no secrets or PII.
- **async** helps **I/O-bound** work (LLM, DB, HTTP calls). Not CPU-bound. **Never block the event loop** (`time.sleep`, `requests`).

## 🌐 HTTP

```
METHOD /path?query  + headers + body   →   STATUS + headers + body
```

| Code | Meaning | Retry? |
|---|---|---|
| 2xx | OK | — |
| 400 / 422 | Bad request / failed validation | ❌ fix request |
| 401 / 403 | Not authenticated / not allowed | ❌ |
| 404 | Not found | ❌ |
| **429** | Rate limited | ✅ after `Retry-After`, with backoff |
| 500 | Server bug | ⚠️ cautiously |
| **502 / 503 / 504** | Upstream failed / overloaded / timed out | ✅ with backoff |

- **Idempotent** = safe to repeat. `POST` isn't, so use an `Idempotency-Key`.
- Always: **timeouts**, `raise_for_status()`, **request IDs**, input **size limits**.
- Never return errors with status 200.

## 📈 ML basics

- Features → model → prediction. Training is offline; inference is per request. The model is an **artifact**.
- **Split**: train (fit) / validation (tune) / test (final check). **Stratify** rare classes. Use time-based splits for time-ordered data.
- **Overfitting** = train ≫ test. **Underfitting** = bad on both.
- **Accuracy lies on rare events.** Always compare with a dumb baseline.

|  | Pred. fraud | Pred. not fraud |
|---|---|---|
| **Fraud** | TP | FN (missed) |
| **Not fraud** | FP (false alarm) | TN |

- **Precision** = TP / (TP + FP): "of what we flagged, how much was fraud?"
- **Recall** = TP / (TP + FN): "of all fraud, how much did we catch?"
- **Threshold** ↓ → recall ↑, precision ↓. Choosing it is a **business** decision.
- **Leakage**: if you wouldn't know it *at prediction time*, it's not a feature (`chargeback_filed`).
- Put preprocessing **in the pipeline** to avoid training/serving skew.

## 🤖 LLM basics

- **Token** ≈ 4 English characters ≈ 0.75 words. Price, limits, latency and context are all in tokens.
- LLM = **next-token predictor**. No database, has a training cutoff, optimises *plausible*, not *true* → **hallucination**.
- **Temperature** low = focused, high = varied. **Top-p** = sample from the top cumulative-p tokens. Neither guarantees truth.
- **Context window** = input + output limit. Bigger contexts cost more, are slower, and can bury information.
- **Embeddings** = meaning as vectors; **cosine similarity** = closeness. Lexical (words) vs semantic (meaning) → combine both: **hybrid**.
- **RAG** = retrieve your passages → put them in the prompt → answer with citations. Reduces hallucination; doesn't eliminate it.
- **Cost per call** = in/1M × in_price + out/1M × out_price. In RAG, the **context usually dominates**.
- **TTFT** (time to first token) vs **total time**; streaming improves perceived latency.
- Code against **one LLM interface**: `fake` (tests) · `ollama` (local) · `openai` (any OpenAI-compatible API).

## 🔢 Numbers from Lab 0 worth remembering

| Fact | Value |
|---|---|
| Baseline fraud rate | 1.41% (141 frauds in a 10,000-row test set) |
| "Always not fraud" accuracy | 98.59%, recall 0% |
| Logistic regression @0.5 | 1 / 141 frauds caught |
| Logistic regression @0.1 | 23 caught, 110 false alarms |
| Unlimited decision tree | 100% train recall vs 7% test recall |
| "refund a fee" vs "get my money back…" | hash 0.000 · MiniLM 0.719 |

---
⬅️ [Quiz](quiz.md) · ➡️ [Module 1: From Prototype to Production](../01-prototype-to-production/README.md)
