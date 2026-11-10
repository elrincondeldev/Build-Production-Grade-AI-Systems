# Postmortem: fraud scoring timeouts after the v2 model rollout (simulated)

> **Severity:** SEV2 · **Duration:** 47 minutes · **Status:** action items in progress
> **Authors:** on-call primary, Incident Commander · **Review meeting:** within 5 business days
> **Blameless:** this document describes how the *system* allowed the failure. It does not assign fault to individuals.

*This is a teaching example about the fictional Kestrel Pay. Use it as a model for your own (template: `templates/postmortem.md` at the repo root).*

## Summary

A new fraud model (v2) with 3× more features was rolled out with a canary. Its p95 latency was 35% higher than v1, but the canary analysis only checked the error rate, so the rollout reached 100%. At peak traffic, scoring exceeded the payment gateway's 200 ms timeout for about 9% of requests. Those requests fell back to rule-based scoring, which declined more legitimate transactions than usual. No money was lost, but about 1,900 customers saw a declined card payment they had to retry.

## Impact

- 9% of authorisations scored by fallback rules for 47 minutes
- Roughly 1,900 extra false declines (estimated from the fallback rule's known false-positive rate)
- Fraud-service latency SLO: **31%** of the monthly error budget consumed in one incident

## Timeline (CET)

| Time | Event |
|---|---|
| 14:02 | Rollout of fraud model v2 starts: 5% canary |
| 14:17 | Analysis passes (error rate 0.1%) → 25% |
| 14:32 | Analysis passes → 100%. p95 latency has risen from 92 ms to 124 ms, which no check looks at |
| 17:05 | Evening peak begins; CPU at 80%; HPA scales from 6 to 10 pods (max) |
| 17:11 | 🔔 `FraudScoringLatencyBurnRate` fast-burn page (1h burn 16×, 5m burn 22×) |
| 17:14 | On-call acknowledges, opens the runbook, sees a deploy 3 hours earlier |
| 17:19 | SEV2 declared, IC assigned |
| 17:24 | `kubectl argo rollouts undo`: rollback to v1 starts |
| 17:41 | Rollback complete; p95 back to 95 ms |
| 17:58 | Alert resolves; incident closed |

## Root causes and contributing factors

1. **The canary analysis did not check latency.** The AnalysisTemplate only had an error-rate metric. *Why?* The template was copied from a service with no latency SLO.
2. **The canary ran at off-peak traffic.** A +35% latency increase only became a timeout problem at peak load. *Why?* There is no rule about the time of day for model rollouts.
3. **HPA maximum too low** for a model that is more expensive per request. Capacity was planned for v1's cost per request.
4. **Detection took 2.5 hours from the regression**, because latency was still inside the SLO until the peak.

## What went well

- Graceful degradation worked: payments never stopped.
- The burn-rate alert paged within 6 minutes of real customer impact.
- The rollback took one command and 17 minutes.

## Action items

| # | Action | Type | Owner | Due |
|---|---|---|---|---|
| 1 | Add a p95-latency-ratio metric (≤ 1.20× stable) to the canary AnalysisTemplate | Prevent | AI Platform | 1 week |
| 2 | Require a load test at 2× peak for any model whose features or size change | Prevent | ML team | 2 weeks |
| 3 | Re-run the capacity plan with v2's GPU/CPU seconds per request; raise HPA max | Mitigate | SRE | 1 week |
| 4 | Add "cost per request" to the model card and the release checklist | Process | ML team | 2 weeks |
| 5 | Alert on latency *regression vs last week* (ticket, not page) | Detect | SRE | 3 weeks |

## Lessons

- A canary only protects you against the failures it *measures*.
- Off-peak canaries miss load-dependent failures; combine them with load tests.
- Model changes are capacity changes.
