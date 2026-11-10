---
doc_id: incident-response-runbook
title: Incident Response Runbook
access: engineering
owner: SRE
updated: 2026-10-01
---

# Incident Response Runbook

## Severity levels

| Severity | Definition | Response time | Example |
|---|---|---|---|
| SEV1 | Customer money or data at risk, or core payments down | 5 minutes, 24/7 | Card authorisations failing |
| SEV2 | Major feature degraded for many users | 15 minutes, 24/7 | Fraud scoring timing out, fallback rules active |
| SEV3 | Minor degradation, workaround exists | Next business day | Docs assistant slow |

## Roles

- **Incident Commander (IC):** coordinates, decides, does not debug.
- **Communications lead:** posts updates every **30 minutes** for SEV1 and every **60 minutes** for SEV2 in #incidents and on the status page.
- **Operations lead:** hands on keyboard.

## Steps

1. Declare the incident in #incidents with `/incident declare`.
2. Stabilise first: roll back, fail over or switch to the fallback. Root cause comes later.
3. Every SEV1 and SEV2 gets a **blameless postmortem** within **5 business days**.
