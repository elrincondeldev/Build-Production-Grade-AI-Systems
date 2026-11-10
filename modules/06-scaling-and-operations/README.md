# Module 6: Scaling and Operations

> ⏱ ~12 hours (7 lessons × 45–75 min + a 3–5 hour lab) · 🎚 Core → Advanced

[Course home](../../README.md) › Module 6

*Release to a slice of traffic, roll back automatically, keep humans in the loop, and cost it all out.*

## 🧭 Where you are

```mermaid
flowchart LR
    M0["0 · Foundations"] --> M1["1 · Prototype → Production"] --> M2["2 · Data & Model Pipelines"] --> M3["3 · Serving & Optimization"] --> M4["4 · Evaluation & Monitoring"] --> M5["5 · Security & Governance"] --> M6["6 · Scaling & Operations<br/>📍 YOU ARE HERE"] --> C["🏆 Capstone"]
    classDef done fill:#d1fae5,stroke:#059669,color:#064e3b
    classDef here fill:#fde68a,stroke:#d97706,stroke-width:3px,color:#78350f
    classDef next fill:#e5e7eb,stroke:#6b7280,color:#111827
    class M0,M1,M2,M3,M4,M5 done
    class M6 here
    class C next
```

## 📨 The story so far

You've turned Sam's prototypes into real services: versioned, containerised, evaluated, monitored and locked down. Now Kestrel wants to **depend** on them:

> **From: Maya (Engineering Manager)**
> Leadership signs off the AI platform at the end of the month. The questions will be operational:
> *Can it run on our Kubernetes clusters? What does it cost at 3× traffic? How do we release without another "Tuesday incident"? Who gets paged, and what do they do?*
> And Lena wants the refund agent, which Priya will only accept with a human approving risky actions.
> This module is about running AI systems as a **business-critical platform**, not a project.

## 🎯 Module objectives

By the end of this module you can:

1. **Deploy** AI services on Kubernetes with correct probes, resources, autoscaling and disruption budgets, and **choose** between managed Kubernetes, ECS and managed ML platforms
2. **Orchestrate** training pipelines as idempotent DAGs, and **choose** between Airflow, Prefect, Dagster, Kubeflow and Ray
3. **Plan** GPU capacity from first principles (Little's Law, GPU-seconds per request, headroom) and **compare** API vs self-hosted cost
4. **Release** safely with canary and blue-green strategies, **automatic rollback gates**, and statistically sound canary analysis
5. **Define** SLOs (latency, errors, groundedness), error budgets and **multi-window burn-rate alerts**
6. **Run** incidents and write runbooks and **blameless postmortems**, including AI-specific failure modes
7. **Decide** when *not* to use an agent, and **build** a planner/worker agent with tracing, hard limits and human approval gates
8. **Design** recommendation, risk-scoring and consumer-assistant systems with a repeatable framework

## 📖 Lessons

| # | Lesson | You'll learn | Time |
|---|---|---|---|
| 6.1 | [Kubernetes and managed ML platforms](01-kubernetes-and-managed-platforms.md) | Reconciliation, the 7 objects you need, probes, requests/limits, Kustomize; EKS/GKE/AKS vs ECS; Vertex AI, SageMaker, Azure ML | 60 min |
| 6.2 | [Workflow orchestration](02-workflow-orchestration.md) | DAGs, idempotency, backfills; Airflow vs Prefect vs Dagster vs Kubeflow vs Ray; continuous training | 50 min |
| 6.3 | [GPUs, autoscaling and capacity planning](03-gpus-autoscaling-and-capacity.md) | GPU scheduling, node pools, HPA/KEDA/Karpenter, scaling signals for LLMs, Little's Law, capacity and cost maths | 60 min |
| 6.4 | [Release engineering and SLOs](04-release-engineering-and-slos.md) | Deploy vs release, canary and blue-green, auto-rollback gates, small-sample statistics, SLOs, error budgets, burn rates | 70 min |
| 6.5 | [Incident response and on-call](05-incident-response-and-on-call.md) | Severities, roles, mitigate-first, AI-specific incidents, runbooks, blameless postmortems, humane on-call | 45 min |
| 6.6 | [Agents in production](06-agents-in-production.md) | Workflows vs agents, when not to use agents, planner/worker, HITL gates, limits, tracing, agent evals | 70 min |
| 6.7 | [Case studies](07-case-studies.md) | A 9-step design framework; recommendation and search, fintech risk scoring, consumer assistants | 75 min |

## 🛠 Lab 6: Deploy the platform with a canary, a cost report and a supervised agent

[**Open the lab →**](lab/README.md)

You will:

- Run the `kestrel-platform` service with health, readiness, metrics and **fault injection**
- Render Kubernetes manifests for `dev` and `prod` with Kustomize (no cluster required), and optionally deploy to kind or minikube
- Ship an **Argo Rollouts canary** (5% → 25% → 100%) with a Prometheus-based rollback gate
- **Simulate** good and bad releases locally and watch the canary analysis promote, hold or roll back
- Compute **error budgets and burn-rate alerts**
- Run a training pipeline as a **DAG** (and as a Prefect flow)
- Produce a **capacity plan** and an **API-vs-self-host cost report**
- Operate a **refund agent** with tracing, limits and a **human approval gate**
- Study a **runbook** and a **blameless postmortem**

### ✅ Definition of Done

- [ ] `cd modules/06-scaling-and-operations/lab && uv sync && uv run pytest` passes
- [ ] You ran the canary simulation in all three modes and can explain each decision from its confidence interval
- [ ] You can explain every difference between the `dev` and `prod` overlays
- [ ] You can explain the burn-rate alert table, including why each alert has two windows
- [ ] You generated `reports/cost-report.md` from assumptions you edited and can defend
- [ ] You approved one agent action via the CLI and one via the approvals file, and read the trace
- [ ] You wrote a runbook for a new alert (lesson 6.5, *Try it* #3)
- [ ] You wrote a one-page design for one case study (lesson 6.7, *Try it* #1)

## 📊 Self-assessment

Rate yourself before and after the module. **1** = never heard of it · **2** = I recognise it · **3** = I can do it with notes · **4** = I could teach it.

| Skill | Before | After |
|---|:-:|:-:|
| Explain Kubernetes reconciliation and the role of each probe | | |
| Set requests/limits and an HPA for a CPU service, and the right scaling signal for an LLM server | | |
| Choose between managed K8s, ECS and a managed ML platform for a given team | | |
| Build an idempotent pipeline DAG and pick an orchestrator | | |
| Size GPU replicas and monthly cost from traffic and throughput | | |
| Design a canary with automatic rollback, including small-sample reasoning | | |
| Define SLOs and burn-rate alerts, including a quality SLO | | |
| Lead an incident, write a runbook and a blameless postmortem | | |
| Decide when not to use an agent; design HITL gates and limits | | |
| Design a recommender, a risk-scoring system or a consumer assistant end to end | | |

Anything still at 1–2 after the module? Re-read that lesson's *Key takeaways* and redo its *Check yourself*.

## 🎤 Interview corner

This module prepares you for these common ML/AI system design and operations questions:

1. *"Design a fraud detection system for card payments."* → lesson 6.7 B; emphasise the latency budget, fallbacks, delayed labels and cost-based thresholds.
2. *"Design a recommendation system for an e-commerce home page."* → lesson 6.7 A; the multi-stage funnel, feedback loops, online evaluation.
3. *"How would you safely roll out a new model version?"* → lesson 6.4; shadow → canary with technical and ML-behaviour gates → SLO monitoring, with small-sample reasoning.
4. *"How many GPUs do you need to serve an LLM at X requests per second?"* → lesson 6.3; Little's Law and GPU-seconds per request, headroom, N+1, and "I'd measure throughput with a load test".
5. *"Would you build this as an agent?"* → lesson 6.6; start from "what's the lowest level of autonomy that solves it?", then HITL, limits, tracing.

## 📄 Also in this module

- [Module quiz](quiz.md): 14 questions, including spaced review from earlier modules
- [Cheat sheet](cheatsheet.md): one page to keep

---
⬅️ [Module 5: Security and Governance](../05-security-and-governance/README.md) · ➡️ [Lesson 6.1](01-kubernetes-and-managed-platforms.md) · 🏆 [Capstone](../../capstone/README.md)
