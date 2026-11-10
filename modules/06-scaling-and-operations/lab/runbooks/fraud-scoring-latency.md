# Runbook: fraud-service p95 latency / timeout alert

> **Service:** fraud-service (kestrel-platform `/v1/score`) · **Owner:** AI Platform team · **Severity if customer impact:** SEV2
> **Alert:** `FraudScoringLatencyBurnRate` (fast burn: 1h and 5m burn rate ≥ 14.4× on the latency SLO)
> **SLO:** 99% of `/v1/score` requests complete in < 150 ms over 30 days

Every alert must link to a runbook, and this is the one for that alert. Keep it short enough to follow at 03:00.

## 1. Is it real? (2 minutes)

- [ ] Open the *fraud-service overview* dashboard. Is p95 latency above 150 ms **for the last 10 minutes**, not just one spike?
- [ ] Is the error rate also up? (Timeouts at the payment gateway show up as 5xx/599 there.)
- [ ] Is traffic unusual? Compare requests/s with the same hour last week.

If none of these hold, it is probably a noisy alert: acknowledge it, file a ticket to tune the alert, and stop here.

## 2. Stabilise first (5 minutes): mitigation before diagnosis

Do the **first** action that applies, then check the dashboard again:

| Symptom | Action | Command |
|---|---|---|
| A deploy or rollout happened in the last 2 hours | Roll back | `kubectl argo rollouts abort kestrel-platform -n kestrel-prod` then `kubectl argo rollouts undo kestrel-platform -n kestrel-prod` |
| CPU above 85% on all pods and the HPA is at max replicas | Raise the HPA ceiling | `kubectl patch hpa kestrel-platform -n kestrel-prod -p '{"spec":{"maxReplicas":30}}'` |
| Pods in `CrashLoopBackOff` or not `Ready` | Check events | `kubectl describe pod -l app=kestrel-platform -n kestrel-prod` |
| Feature store or model registry is slow | Switch to fallback rules | set `KESTREL_SCORING_MODE=rules` in the ConfigMap and restart (real fraud-service only; the lab app has no rules mode) |

> The payment gateway calls fraud scoring with a **200 ms timeout** and falls back to rule-based scoring when it times out (graceful degradation, lesson 1.3). Customers can still pay; we are just scoring less accurately. That is why this is SEV2, not SEV1.

## 3. Declare and communicate

- If customer impact lasts more than 10 minutes: `/incident declare sev2 "fraud scoring latency"` in #incidents.
- The Incident Commander posts updates every **60 minutes** for SEV2 (see the Incident Response Runbook).

## 4. Diagnose (after stabilising)

- `kubectl top pods -n kestrel-prod -l app=kestrel-platform`: CPU or memory pressure?
- Traces: open the slowest traces for `/v1/score`. Which span dominates: feature fetch, model inference, or serialisation?
- `kubectl get events -n kestrel-prod --sort-by=.lastTimestamp | tail -20`: evictions, node pressure, image pulls?
- Did the input distribution change? Large `amount` values or a new merchant category can push the model onto slow code paths.

## 5. Close out

- [ ] Alert resolved for 30 minutes
- [ ] Fallback mode switched off (if used)
- [ ] Postmortem scheduled within 5 business days (all SEV1 and SEV2 incidents)
- [ ] This runbook updated with anything that was missing or wrong
