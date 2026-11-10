# Design doc: <system name>

| | |
|---|---|
| **Author(s)** | |
| **Reviewers** | |
| **Status** | Draft · In review · Approved · Superseded |
| **Last updated** | YYYY-MM-DD |

## 1. Context and problem
What is the problem, who has it, and why now? Link tickets and data. 3–6 sentences.

## 2. Goals and non-goals
- **Goals:** measurable outcomes (e.g. "answer 80% of tier-1 support questions with ≥ 0.9 faithfulness").
- **Non-goals:** what this design deliberately does *not* do.

## 3. Requirements
| Type | Requirement | Target |
|---|---|---|
| Functional | | |
| Latency | p95 end-to-end | e.g. < 2.5 s |
| Availability | SLO | e.g. 99.5% monthly |
| Quality | Offline eval metric | e.g. recall@5 ≥ 0.85 |
| Cost | Per request / per month | |
| Security & privacy | Data classes handled, access rules | |

## 4. Proposed design
- Architecture diagram (mermaid).
- Request flow for the main use case, step by step.
- Data flow: sources, pipelines, storage, retention.
- Model and prompt choices, and the adaptation strategy (prompt / RAG / fine-tune) with justification.

## 5. Alternatives considered
| Option | Pros | Cons | Why not chosen |
|---|---|---|---|

## 6. Evaluation plan
Offline metrics and golden sets, online metrics, eval gates, how a release is approved.

## 7. Operations
Observability (SLIs, dashboards, alerts), rollout plan (shadow → canary → full), rollback, on-call and runbooks.

## 8. Security, privacy and governance
Threat model (OWASP LLM Top 10 mapping), authN/Z, PII handling, guardrails, audit, regulatory notes, model card link.

## 9. Cost
Assumptions (traffic, tokens per request, cache hit rate), unit cost, monthly cost, API vs self-hosted comparison, and cost levers.

## 10. Risks and open questions
| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|

## 11. Milestones
| Milestone | Scope | Date |
|---|---|---|
