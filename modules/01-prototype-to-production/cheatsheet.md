# Module 1 cheat sheet: From Prototype to Production

[Course home](../../README.md) › [Module 1](README.md) › Cheat sheet

## Prototype → production (1.1)
- The model is ~5–10% of the system. The rest: data, packaging, serving, monitoring, security, operations.
- **Lifecycle loop:** data → features/context → train/adapt → evaluate → package → serve → monitor → back to data.
- **Training/serving skew causes:** two code paths · leakage (info not available at prediction time) · different data source/freshness · different library versions.
- **Fixes:** one shared feature function · feature contract checked at load · deny-list of leaky columns + test · log served features · feature store · time-based splits.
- **Handoff = artifacts + metadata**, not a pickle. Pass the "bus test".

## Architecture (1.2)
| Mode | When | Kestrel |
|---|---|---|
| Batch | Nobody waits; staleness OK | Nightly account re-scoring, doc indexing |
| Online | Someone waits; request-time data | `POST /v1/score` |
| Streaming | Fresh in seconds; nobody blocks | `transaction.scored` consumers |
- Modular monolith first; split for release cadence, scaling, hardware, isolation, ownership.
- Event consumers must be **idempotent** (at-least-once delivery).
- Keep services **stateless**; state goes in shared stores.
- Building blocks: **API gateway · feature store · vector DB · model registry · queue/stream · object storage · experiment tracker · observability · prompt registry**.
- **Write a latency budget first.** Network calls, not the model, dominate.

## Reliability (1.3)
- n deps at p each → availability pⁿ (5 × 99.9% ≈ 99.5%). **Slow is worse than down.**
- **Timeouts on every call** (connect short, read ≈ 2–3× dependency p99) + a **deadline** for the whole operation.
- Retry: timeouts, connection errors, 429, 5xx. **Never** 4xx. Non-idempotent → idempotency key.
- `sleep = uniform(0, min(cap, base × 2^(n−1)))`: exponential backoff + **full jitter**.
- Retry at **one layer**; cap attempts (2–3); **retry budget** (≈10% extra load); circuit breaker for hard-down deps.
- Queues: smooth bursts, decouple, backpressure, DLQ for poison messages.
- **Degradation ladder** agreed with the business; always flag `degraded`. Fail open/closed is a business call.
- REST by default; **gRPC** for measured high-throughput internal calls and strict contracts.
- **Stream** LLM output via SSE; stop on disconnect; beware proxy buffering; measure TTFT separately.

## Services (1.4)
```
api/      HTTP ↔ domain (schemas, status codes, middleware)
domain/   rules in pure Python; defines Protocols (ports)
adapters/ files, HTTP, LLMs; implement the ports
main.py   create_app(): composition root + lifespan (load once)
```
- Config in env vars (`KESTREL_*`), typed and validated at startup; one image for all environments.
- Secrets: not in code, Git, images or logs. `SecretStr`. Secret manager in prod. Rotate leaks.
- `async` for I/O-bound work; `asyncio.gather` for independent calls; **never block the loop** (sync clients, `time.sleep`, heavy CPU → thread/process pool); cap concurrency.
- JSON logs with stable `event` names; request ID from header (validated) or generated, bound to logs, forwarded downstream, returned to the client.
| Probe | Fails → | Checks |
|---|---|---|
| Liveness `/health` | restart | process answers; **never** dependencies |
| Readiness `/ready` | no traffic | model loaded + verified |
| Startup | delay liveness | slow boot allowance |

## Artifacts & containers (1.5)
- pickle/joblib **can execute code**: own artifacts only, verify sha256 **before** load, pin versions; prefer ONNX/safetensors/native formats.
- Artifact = **immutable, unique version, self-describing metadata, verifiable hash**. Atomic `LATEST` pointer (write temp + rename). Pin explicit versions in prod.
- sha256 proves **integrity**, not authorship (→ signatures) or quality (→ evals).
- Dockerfile: slim pinned base · lockfile · **deps before code** · multi-stage · **non-root** · `.dockerignore` · no secrets in layers · exec-form CMD · HEALTHCHECK.
- Tags are mutable, **digests** aren't. Never deploy `:latest`.
- K8s: **Deployment** (replicas, rolling update) · **Service** (stable name → ready pods) · **ConfigMap/Secret** · **probes** · **requests/limits** · **securityContext**.

## Commands you used
```bash
uv run python scripts/train.py                        # versioned artifact
shasum -a 256 artifacts/fraud-model/*/model.joblib    # verify / compare
uv run pytest                                         # 32 tests
uv run uvicorn kestrel_fraud.main:create_app --factory --port 8001
uv run python scripts/fake_feature_store.py --fail-rate 0.4
curl -N localhost:8001/v1/explain/<transaction_id>    # SSE stream
docker build -t kestrel/fraud-service:0.1.0 .
docker run --rm -p 8001:8001 kestrel/fraud-service:0.1.0
```

⬅️ [Module 1 overview](README.md) · 📝 [Quiz](quiz.md)
