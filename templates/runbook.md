# Runbook: <alert name>

| | |
|---|---|
| **Service** | |
| **Severity when firing** | SEV1 / SEV2 / SEV3 |
| **Dashboard** | link |
| **Owner** | team |

## What this alert means
One paragraph, in plain words. What is the user impact?

## Check first (≤ 5 minutes)
1. Is it real? Check the dashboard panel …
2. Did anything change? Recent deploys, prompt/model releases, config changes, upstream incidents.
3. How big is it? Share of traffic and users affected.

## Mitigate (stabilise before you investigate)
| Situation | Action | Command / link |
|---|---|---|
| Started right after a release | Roll back | |
| Dependency down | Enable fallback / degrade gracefully | |
| Traffic spike | Scale out / shed load | |

## Investigate
Logs and trace queries to run, and common root causes seen before.

## Escalate
Who to page next, and when.

## After the incident
Open a postmortem if SEV1/SEV2. Update this runbook with anything that was missing.
