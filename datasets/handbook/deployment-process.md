---
doc_id: deployment-process
title: Deployment Process
access: engineering
owner: Platform Team
updated: 2026-09-18
---

# Deployment Process

- All services deploy through the CI/CD pipeline. Manual `kubectl apply` in production is forbidden except during a declared incident.
- Every change needs **one approving review** and green CI (tests, lint, security scan, eval gate for ML/LLM services).
- Production releases use a **canary**: 5% of traffic for 15 minutes, then 25%, then 100%. Automatic rollback triggers if the error rate rises above **1%** or p95 latency rises more than **20%** against the baseline.
- **Deploy freeze**: no production deploys on Fridays after 15:00 CET or during the last **3 business days** of the month (payments peak), except fixes for SEV1/SEV2.
- Model and prompt changes follow the same process as code changes.
