import pandas as pd
import pytest

from pipelines.validate import DataValidationError, feature_columns, gate, validate


def test_clean_generated_data_passes_the_gate(raw_df):
    clean = gate(raw_df)
    assert len(clean) == len(raw_df)
    assert clean["amount"].dtype == "float64"


def test_bad_rows_are_detected_and_quarantined(raw_df):
    bad = raw_df.copy()
    bad.loc[0, "amount"] = -50.0                    # negative amount
    bad.loc[1, "merchant_category"] = "casino"      # unknown category
    bad.loc[2, "hour"] = 25                         # out of range
    bad.loc[3, "card_age_days"] = None              # null in non-nullable column
    report, valid, quarantined = validate(bad)
    assert report.row_errors["amount:below_min"] == 1
    assert report.row_errors["merchant_category:unknown_value"] == 1
    assert report.row_errors["hour:above_max"] == 1
    assert report.row_errors["card_age_days:null"] == 1
    assert len(quarantined) == 4 and len(valid) == len(bad) - 4
    # 4 bad rows out of 5,000 is below the 1% tolerance, so the gate lets clean rows through.
    assert len(gate(bad)) == len(bad) - 4


def test_gate_fails_when_too_many_rows_are_bad(raw_df):
    bad = raw_df.copy()
    bad.loc[: len(bad) // 10, "amount"] = -1.0  # 10% broken, e.g. an upstream unit change
    with pytest.raises(DataValidationError) as exc:
        gate(bad)
    assert "rows failed checks" in str(exc.value)


def test_gate_fails_on_dataset_level_problems(raw_df):
    with pytest.raises(DataValidationError, match="missing columns"):
        gate(raw_df.drop(columns=["amount"]))
    with pytest.raises(DataValidationError, match="duplicate transaction_id"):
        gate(pd.concat([raw_df, raw_df.head(10)]))
    no_fraud = raw_df.assign(is_fraud=0)
    with pytest.raises(DataValidationError, match="fraud rate"):
        gate(no_fraud)


def test_feature_contract_excludes_identifiers_labels_and_post_label_fields():
    feats = feature_columns()
    assert "chargeback_filed" not in feats
    assert "is_fraud" not in feats
    assert "transaction_id" not in feats
    assert "amount" in feats


def test_distribution_check_catches_unit_change(raw_df):
    cents = raw_df.assign(amount=raw_df["amount"] * 100)  # upstream switched euros -> cents
    report, _, _ = validate(cents)
    # Per-row range checks catch only the few huge purchases (< 1%)...
    assert report.bad_row_fraction < 0.01
    # ...the dataset-level median check is what stops the run.
    with pytest.raises(DataValidationError, match="amount median"):
        gate(cents)
