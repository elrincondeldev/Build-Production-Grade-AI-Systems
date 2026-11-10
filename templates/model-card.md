# Model card: <model name> v<version>

> Based on *Model Cards for Model Reporting* (Mitchell et al., 2019). Keep it short and honest; "unknown" is a valid answer.

## Model details
- **Owner / contact:**
- **Version, date, artifact sha256:**
- **Type:** (e.g. gradient-boosted trees, binary classifier)
- **Training code commit / data digest / environment lock:**

## Intended use
- **Primary use:**
- **Primary users:**
- **Out-of-scope uses:** (things it must NOT be used for)

## Training data
Source, time range, size, label definition, known gaps. Link the datasheet.

## Evaluation
| Metric | Value | Dataset / slice | Notes |
|---|---|---|---|
| PR-AUC | | test, overall | |
| Recall @ chosen threshold | | | |
| Precision @ chosen threshold | | | |
| Brier score | | | Calibration |

Decision threshold and how it was chosen (cost model):

## Performance across groups (fairness)
Slices evaluated (e.g. country, card age, merchant category), metric gaps found, and decisions taken.

## Limitations and risks
Known failure modes, drift sensitivity, adversarial risks.

## Monitoring and retraining
What is monitored, alert thresholds, retraining trigger, rollback plan.

## Ethical and regulatory considerations
Human oversight, explanations given to users, applicable regulation.
