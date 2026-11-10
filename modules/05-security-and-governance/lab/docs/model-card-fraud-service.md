# Model Card: `fraud-service` transaction risk model

> Filled-in example for lesson 5.6. The structure follows *Model Cards for Model Reporting* (Mitchell et al., 2019), adapted for an internal production system. Numbers come from `scripts/fairness_audit.py` on the synthetic baseline dataset (seed 42) and **will differ from yours** if you change the model or data.

| Field | Value |
|---|---|
| Model name / version | `fraud-logreg` v0.5.0 (artifact sha256 recorded in the model registry) |
| Owner | Kestrel Pay AI Platform team (you); business owner: Omar (Risk) |
| Reviewers | Priya (Security & compliance), Diego (SRE) |
| Last updated | 2026-12-01 |
| Status | Shadow mode. Not yet allowed to block payments on its own |

## 1. Intended use

- **Primary use:** score card transactions in real time (p95 budget: 50 ms) and send high-risk ones to **manual review** or step-up authentication (e.g. a 3-D Secure challenge).
- **Primary users:** the payments authorisation service (machine) and Risk analysts (human).
- **Out of scope:** credit decisions, account closure, any decision without human review, and use on non-card products. The model has never seen data from them.

## 2. Model details

- Logistic regression on 10 tabular features (standardised numeric + one-hot merchant category).
- **Excluded on purpose:** `chargeback_filed`, a leaky feature only known after the label exists (see lesson 2.2), and `customer_id` (memorisation risk, no generalisation).
- Decision threshold: `P(fraud) ≥ 0.10` → flag for review. The threshold was chosen by a cost sweep (lesson 4.2), not by default.

## 3. Training and evaluation data

- Synthetic Kestrel Pay transactions (`datasets/fraud/generate.py`, baseline scenario), 50,000 rows, about 1.4% fraud. 70/30 stratified split.
- Known gaps: one home country (ES); no seasonality; no card-testing pattern (it appears in the `concept_drift` scenario, see lesson 4.5).

## 4. Metrics

| Metric | Value | Notes |
|---|---|---|
| PR-AUC | see your MLflow run | Primary offline metric: the base rate is low, so ROC-AUC is misleading |
| Flag rate | 1.3% overall | Drives the review team's workload |

## 5. Fairness analysis: "domestic" vs "abroad" transactions

`country_mismatch` is not a protected attribute, but it is a **proxy** for nationality and migrant status, people who are more likely to pay from abroad. So we audit it.

| Group | Transactions | Fraud rate | False positive rate | True positive rate | Flag rate |
|---|---|---|---|---|---|
| abroad | 733 | 7.4% | **20.9%** | 55.6% | 23.5% |
| domestic | 14,267 | 1.1% | **0.2%** | 1.9% | 0.2% |

**Findings.**
1. A legitimate customer paying abroad is about **98× more likely** to be wrongly flagged than one paying at home. The real fraud rate is only about 6.7× higher. The single global threshold amplifies the gap.
2. The model catches **almost no domestic fraud** (TPR 1.9%) at this threshold. Most fraud losses come from the domestic group because it is 19× larger.

**Decision (Omar, Priya, 2026-12-01):** not acceptable for automatic blocking. Actions: (a) stay in shadow mode; (b) evaluate per-segment thresholds and a better model (gradient boosting with interaction features); (c) step-up authentication instead of a hard decline for the `abroad` group; (d) re-audit before every release, with this table as a CI artifact.

## 6. Explainability

- Global: coefficients of the logistic regression (sign and size per standardised feature) are published to Risk.
- Local: each flag includes the top 3 contributing features (`coef × value`) so a reviewer can see *why*, e.g. "new device, crypto exchange, 03:00".

## 7. Risks, limitations and monitoring

- **Drift:** monitored daily with PSI on inputs and weekly on label-delayed precision (lesson 4.5).
- **Feedback loop:** flagged transactions get reviewed, so their labels are better than unflagged ones'. Keep a small random holdout sample reviewed regardless of score.
- **Regulatory note:** under the EU AI Act, AI systems used *to detect financial fraud* are explicitly excluded from the high-risk "creditworthiness" use case (Annex III). This is **not** a blanket exemption from GDPR, non-discrimination law or PSD2 strong-customer-authentication rules. Confirm with Legal; this card is not legal advice.

## 8. Change log

| Version | Date | Change | Approved by |
|---|---|---|---|
| 0.5.0 | 2026-12-01 | First card, fairness audit added | Priya |
