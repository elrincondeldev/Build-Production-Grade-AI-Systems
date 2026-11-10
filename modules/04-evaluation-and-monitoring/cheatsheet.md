# Module 4 cheat sheet: Evaluation and Monitoring

[Course home](../../README.md) › [Module 4](README.md) › Cheat sheet

## Classification metrics

| Metric | Formula | Use when |
|---|---|---|
| Precision | TP / (TP + FP) | False alarms are expensive |
| Recall | TP / (TP + FN) | Misses are expensive |
| F1 / F-β | (1+β²)PR / (β²P + R) | One number; β > 1 favours recall |
| ROC-AUC | P(score of random positive > random negative) | Comparing rankers; balanced-ish data |
| PR-AUC (average precision) | Area under precision–recall | **Rare events**. Random = base rate, so only compare on the same population |

⚠️ Accuracy on imbalanced data ≈ 1 − base rate. Pass **scores**, not labels, to AUC functions. Split by **time**. Never tune on the test set. **Slice** every metric.

## Thresholds and calibration

- Threshold = **policy** from a cost model. Sweep thresholds on **validation** data and pick the minimum expected cost.
- With calibrated p: **flag if p · loss > review + (1 − p) · friction** (per transaction).
- Calibrated ⇔ "of cases scored p, a fraction p are positive". Check with a **reliability diagram** (quantile bins).
- **Brier** = mean (p − y)²; no-skill = b(1 − b). **ECE** = weighted mean |predicted − observed| per bin.
- Fix: **Platt** (2 params, little data) · **isotonic** (flexible, more data) · **temperature** (neural nets). Fit on held-out data. Ranking (AUC) is unchanged.

## LLM evaluation

```
golden set (categories incl. refuse / unanswerable / injection)
  → deterministic checks → reference scores → LLM judge (calibrated) → humans
  + multi-turn continuity + agent trajectory + red-team pack
  → eval_report.json → eval gate (exit 1 blocks the PR)
```

| Family | Metrics |
|---|---|
| Retrieval | hit rate, context precision/recall |
| Grounding | faithfulness (claims supported by context), citation hit |
| Answer | correctness vs reference, judge pass rate, false-refusal rate |
| Safety | access violations = 0, injection resistance = 1, red-team pass = 1 |
| Agents | tool accuracy, argument accuracy, forbidden calls = 0, memory |

**Judge calibration:** label 50–100 items → confusion matrix + **Cohen's kappa** = (pₒ − pₑ)/(1 − pₑ). < 0.4 weak · 0.4–0.6 moderate · 0.6–0.8 substantial · > 0.8 almost perfect. Re-calibrate when the judge model or rubric changes.

**Gate policy:** safety thresholds absolute · quality floors slightly below baseline, ratcheted up · threshold changes are reviewed (CODEOWNERS) · deterministic in CI, real model nightly.

## Observability

| Signal | Job |
|---|---|
| Metrics | That something is wrong (cheap, aggregated) |
| Traces | Where, inside one request (spans + attributes) |
| Logs | Exact details (structured, shared request/trace ID) |

**Golden signals:** latency · traffic · errors · saturation. **AI signals:** 👎 rate · refusal rate · retrieval score · tokens/cost · cache hit · prompt/model version.

```promql
sum by (route) (rate(kestrel_requests_total[1m]))                                          # traffic
histogram_quantile(0.95, sum by (le) (rate(kestrel_request_latency_seconds_bucket[5m])))  # p95
sum(rate(kestrel_feedback_total{rating="down"}[10m])) / sum(rate(kestrel_feedback_total[10m]))  # 👎 share
```

Counter (only up) · Histogram (distributions) · Gauge (current value). **Bounded labels only** (never user_id or raw paths). Spans use OTel **GenAI conventions** (`gen_ai.request.model`, `gen_ai.usage.input_tokens`). Redact PII in telemetry.

## Drift

| Type | Changes | Detect with |
|---|---|---|
| Data (covariate) | P(X) | PSI, KS per feature; prediction drift |
| Label (prior) | P(y) | Flag rate, late labels; recalibrate |
| Concept | P(y\|X) | **Labels only**: random review holdout, early proxies, outcomes |
| Embedding | Query vectors | Coverage similarity, centroid distance, clustering, emerging terms |
| Prompt | User prompts / your templates | Length, language, topics; registry + eval gate |

**PSI** = Σ (c − r)·ln(c/r): < 0.10 stable · 0.10–0.25 investigate · > 0.25 act. Treat low-cardinality features as categories. Judge KS by the statistic, not the p-value. **Drift ≠ harm.** Step change overnight ⇒ suspect the pipeline.

**Alerts:** page on user-facing symptoms (SLOs); ticket for quality outcomes; dashboard for drift. Use ratios + minimum sample + `for:` + runbook link.

## Releases

- Everything is a change: code · model · prompt · data/index · config. Same pipeline: version → evaluate → progressive rollout → reversible.
- **CT:** trigger → validate data → train challenger → beat the champion on the same data and slices (in €) → register → shadow → canary.
- **Shadow** = copy of traffic, no user impact, stub side effects · **Canary** = small % of real users · **A/B** = canary designed for statistics · **Blue-green** = instant switch and switch-back.
- Canary gates: errors, p95, 👎, refusals, guardrail blocks, cost/request; minimum sample sizes; automated rollback.
- **Prompt registry:** immutable versions · active pointer read per request · audit history · evaluate candidates without activating · rollback in seconds · version on every answer, span and metric.

## Lab commands

```bash
uv run python scripts/threshold_sweep.py          # cost-based threshold
uv run python scripts/calibration.py              # reliability diagram
uv run python -m evals.run_evals [--prompt-version v2] [--agent-memory 0]
uv run python scripts/eval_gate.py                # exit 0 / 1
uv run python -m evals.judge_calibration          # judge vs humans
uv run python scripts/drift_report.py             # PSI, KS, concept, embedding drift
uv run uvicorn kestrel_docs.main:create_app --factory --port 8000
cd observability && docker compose up -d          # Prometheus :9090, Grafana :3000
```

---
⬅️ [Quiz](quiz.md) · ➡️ [Module 5](../05-security-and-governance/README.md)
