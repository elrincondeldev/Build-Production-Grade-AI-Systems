# Module 6 cheat sheet: Scaling and Operations

[Course home](../../README.md) › [Module 6](README.md) › Cheat sheet

## Kubernetes (6.1)

| Object | One-liner |
|---|---|
| Deployment | Keep N identical pods of version X; rolling updates (`maxUnavailable: 0` for zero capacity loss) |
| Service | Stable DNS + load balancing to *ready* pods |
| ConfigMap / Secret | Config outside the image; secrets from a secret manager, never Git |
| HPA | Replicas from metrics (CPU % of *requests*, or custom metrics) |
| PDB | Minimum pods during voluntary disruptions (node drains) |

**Probes:** `startup` = finished starting? (slow model loads) · `readiness` = send traffic now? (no restart) · `liveness` = stuck? (restart). **Never check dependencies in liveness.**
**Resources:** requests drive scheduling; CPU over limit = throttled; memory over limit = OOMKilled. Common choice: memory limit, no CPU limit.
**Platforms:** managed K8s (EKS/GKE/AKS) removes the control plane, not operations · ECS = simpler, AWS-only · Vertex AI / SageMaker / Azure ML = rent the ML lifecycle. Choose **per lifecycle step**.

## Orchestration (6.2)

Cron = *when*. Orchestrator = *what, in which order, retries, skip-downstream, history, backfills.*
Tasks: **idempotent**, explicit partition inputs, write new version then flip pointer, pass references not data.
Airflow (scheduled task DAGs, huge ecosystem) · Prefect (Pythonic flows) · Dagster (data assets, lineage, freshness) · Kubeflow (container steps on K8s) · **Ray = compute, not a scheduler.**
Retraining *registers*; **promotion goes through the release process.**

## Capacity (6.3)

```
Little's Law:        in-flight = arrival rate × latency          (20 rps × 3 s = 60)
GPU-s per request  = input_tokens / prefill_tps + output_tokens / decode_tps
replicas           = max(N+1 floor, ceil(peak_rps × GPU-s / target_utilisation))
monthly cost       = replicas × €/hour × 730
```

GPUs: integer resources (`nvidia.com/gpu: 1`), tainted node pools + tolerations; share via MIG or one multi-model server. Scale LLM servers on **queue depth / in-flight / KV-cache**, not GPU %. Cold starts take minutes: keep a baseline, scale ahead of peaks. **A model change is a capacity change.** Compare API vs self-host *including ops cost*.

## Releases and SLOs (6.4)

| Strategy | Use |
|---|---|
| Rolling | Low-risk changes |
| Blue-green | Instant switch/rollback, 2× capacity |
| **Canary** | Default for models and services: 5% → 25% → 100% with an auto-rollback gate |
| Shadow | Real inputs, zero user impact |
| Feature flag | Prompts, per-segment rollouts, kill switch |

Gate on **technical** (errors, p95) + **ML behaviour** (decline rate, score distribution) + **quality** (groundedness). **Fail fast, pass slow**: rollback if the CI lower bound > limit; promote only if the upper bound < limit with enough samples (~4/limit clean requests, so ~400 for 1%).

```
error budget = 1 − SLO          99.9% / 30 days = 43.2 min
burn rate    = error ratio / (1 − SLO)
```

| Alert | Windows | Burn | Budget if sustained | Action |
|---|---|---|---|---|
| Fast | 1 h **and** 5 min | ≥ 14.4 | 2% in 1 h | Page |
| Medium | 6 h **and** 30 min | ≥ 6 | 5% in 6 h | Page |
| Slow | 3 d **and** 6 h | ≥ 1 | 10% in 3 d | Ticket |

## Incidents (6.5)

Roles: **IC** coordinates (doesn't debug) · **Ops** executes · **Comms** updates on a rhythm.
**Mitigate first:** roll back (code, model, *prompt*, *index*) → fall back/degrade → **kill switch** → scale → block → purge (and **invalidate the semantic cache**).
AI incidents are often **silent**: watch groundedness samples, feedback, retrieval hit rate, guardrail blocks, €/hour.
Pages: urgent, actionable, real (SLO burn), linked to an exact-command runbook. Postmortems: blameless; action items are **system changes** (prevent / detect / mitigate / process).

## Agents (6.6)

Lowest autonomy that works: code → LLM-in-a-step → workflow → constrained agent → open agent.
**Don't use an agent** when the path is known, latency is tight, mistakes are irreversible, or you can't evaluate it.
Planner **proposes** → runtime **validates** (registry, schema) → **gates** (AUTO / REQUIRE_APPROVAL / REFUSE) → executes → observes.
Limits in code: max steps, money budget, idempotency, least privilege, timeouts. Silence = **no**. Trace every decision.

## Case-study framework (6.7)

Requirements → metrics → data (label delay!) → architecture → model → serving (latency budget) → eval and release → operations → risks.
Recsys: retrieve → filter → rank → re-rank; feedback loops; A/B decides. Risk: 200 ms budget + fallback rules, streaming features, cost-based thresholds, delayed labels, adversaries. Consumer assistant: guardrails, permissions, deterministic actions, router + cache, human hand-off.

## Lab commands

```bash
uv run pytest
uv run python scripts/simulate_canary.py --fault errors|latency|none
uv run python -m kestrel_platform.slo --objective 0.999 --ratio 1h=0.02 --ratio 5m=0.03
uv run python -m orchestration.pipeline --rows 20000
uv run python scripts/capacity_plan.py --peak-rps 60 --avg-rps 18
uv run python scripts/cost_report.py
uv run python scripts/run_agent.py --approver cli --show-trace
kubectl kustomize k8s/overlays/prod
```

---
⬅️ [Quiz](quiz.md) · 🏆 [Capstone](../../capstone/README.md)
