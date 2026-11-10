import pytest

from pipelines.digest import dataframe_sha256
from pipelines.leakage import LeakageError, assert_no_leakage, contract_check, scan, statistical_check
from pipelines.validate import feature_columns


def test_statistical_check_flags_chargeback_filed(raw_df):
    findings = statistical_check(raw_df, "is_fraud", ["amount", "chargeback_filed", "merchant_category"])
    assert [f.feature for f in findings] == ["chargeback_filed"]
    assert findings[0].auc > 0.9


def test_contract_check_flags_post_label_and_unknown_columns():
    found = {f.feature for f in contract_check(["amount", "chargeback_filed", "mystery_column"])}
    assert found == {"chargeback_filed", "mystery_column"}


def test_default_features_pass(raw_df):
    assert_no_leakage(raw_df, feature_columns())  # must not raise


def test_assert_no_leakage_raises_for_leaky_feature(raw_df):
    with pytest.raises(LeakageError, match="chargeback_filed"):
        assert_no_leakage(raw_df, feature_columns() + ["chargeback_filed"])


def test_scan_ranks_leaky_feature_first(raw_df):
    assert scan(raw_df).iloc[0]["feature"] == "chargeback_filed"


def test_dataframe_digest_is_order_independent_and_content_sensitive(raw_df):
    d1 = dataframe_sha256(raw_df)
    assert d1 == dataframe_sha256(raw_df[list(reversed(raw_df.columns))])
    changed = raw_df.copy()
    changed.loc[0, "amount"] += 0.01
    assert dataframe_sha256(changed) != d1
