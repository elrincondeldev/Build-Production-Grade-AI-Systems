"""Are the fraud scores real probabilities?  📖 Lesson 4.2.

Compares the uncalibrated model (trained with class_weight="balanced") with
Platt scaling (sigmoid) and isotonic regression, and saves a reliability
diagram to artifacts/reliability.png.

    uv run python scripts/calibration.py
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.metrics import average_precision_score, log_loss, roc_auc_score

from kestrel_fraud.calibration import brier_score, expected_calibration_error
from kestrel_fraud.data import FEATURES, LABEL
from kestrel_fraud.model import make_model

from kestrel_fraud.pipeline import ARTIFACTS, train_or_load


def main() -> None:
    model, train_df, test_df = train_or_load()
    X_train, y_train = train_df[FEATURES], train_df[LABEL]
    X_test, y_test = test_df[FEATURES], test_df[LABEL]

    # Calibrators are fitted with internal cross-validation on TRAIN data only:
    # calibrating on the test set would leak and make the numbers look too good.
    platt = CalibratedClassifierCV(make_model(), method="sigmoid", cv=3).fit(X_train, y_train)
    isotonic = CalibratedClassifierCV(make_model(), method="isotonic", cv=3).fit(X_train, y_train)

    variants = {
        "uncalibrated (balanced)": model.predict_proba(X_test)[:, 1],
        "Platt (sigmoid)": platt.predict_proba(X_test)[:, 1],
        "isotonic": isotonic.predict_proba(X_test)[:, 1],
    }
    base_rate = float(y_test.mean())
    print(f"test fraud rate = {base_rate:.4f}   no-skill Brier = {base_rate * (1 - base_rate):.4f}\n")
    print(f"{'model':<26}{'mean score':>11}{'Brier':>9}{'ECE':>8}{'log loss':>10}{'ROC-AUC':>9}{'PR-AUC':>8}")
    for name, p in variants.items():
        print(
            f"{name:<26}{p.mean():>11.4f}{brier_score(y_test, p):>9.4f}"
            f"{expected_calibration_error(y_test, p):>8.4f}{log_loss(y_test, p):>10.4f}"
            f"{roc_auc_score(y_test, p):>9.3f}{average_precision_score(y_test, p):>8.3f}"
        )

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.plot([0, 1], [0, 1], "k--", label="perfectly calibrated")
    for name, p in variants.items():
        # Quantile bins: equal number of transactions per bin. With 1–3% fraud,
        # uniform bins would leave most high-score bins nearly empty.
        frac_pos, mean_pred = calibration_curve(y_test, p, n_bins=10, strategy="quantile")
        ax.plot(mean_pred, frac_pos, marker="o", label=name)
    ax.set_xlabel("mean predicted probability")
    ax.set_ylabel("observed fraud rate")
    ax.set_title("Reliability diagram (test set)")
    ax.legend(loc="upper left")
    fig.tight_layout()
    ARTIFACTS.mkdir(exist_ok=True)
    out = ARTIFACTS / "reliability.png"
    fig.savefig(out, dpi=120)
    print(f"\nsaved {out}")


if __name__ == "__main__":
    main()
