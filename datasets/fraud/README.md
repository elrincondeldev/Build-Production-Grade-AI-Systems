# Kestrel Pay transactions (synthetic)

Generate the data locally (standard library only, about 2 seconds):

```bash
python datasets/fraud/generate.py                           # baseline -> transactions.csv (50,000 rows, ~1.4% fraud)
python datasets/fraud/generate.py --scenario data_drift     # input distribution shifts
python datasets/fraud/generate.py --scenario concept_drift  # fraud pattern changes (card testing)
```

Generated CSVs are git-ignored; always regenerate them from the script with a fixed `--seed` (this is your first lesson in reproducibility).

| Column | Meaning |
|---|---|
| `amount` | Transaction amount in EUR |
| `merchant_category` | One of 10 categories (grocery, crypto_exchange, …) |
| `hour` | Hour of day, 0–23 |
| `is_online` | 1 if card-not-present |
| `country_mismatch` | 1 if the transaction country differs from the card's country |
| `card_age_days` | Days since card was issued |
| `txn_count_24h` | Customer's transactions in the last 24h |
| `avg_amount_30d` | Customer's average amount over 30 days |
| `device_is_new` | 1 if the device has never been seen for this customer |
| `distance_from_home_km` | Distance from home address |
| `chargeback_filed` | ⚠️ **Leaky**: only known *after* the fraud label exists. Never train on it (lesson 2.2). |
| `is_fraud` | Label |

The label comes from a hidden logistic function in `generate.py` plus noise. As in real fraud, the signal is weak and positives are rare, so **expect modest numbers**: even the true generating function only reaches about **ROC-AUC 0.80 / PR-AUC 0.10** at a ~1.4% base rate, and good models land around ROC-AUC 0.75–0.80 and PR-AUC 0.06–0.10. A PR-AUC of 0.08 is roughly a **6× lift** over random guessing (whose PR-AUC equals the base rate, 0.014), which is genuinely useful for ranking transactions for review. If you ever see PR-AUC near 1.0, suspect leakage (try `chargeback_filed`).
