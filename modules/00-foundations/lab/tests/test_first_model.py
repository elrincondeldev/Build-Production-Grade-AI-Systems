from kestrel_foundations.first_model import (
    EXCLUDED,
    NUMERIC_FEATURES,
    build_baseline,
    build_model,
    evaluate,
    load_transactions,
    overfitting_demo,
    predict_with_threshold,
    split,
)


def test_generated_data_has_rare_fraud(small_fraud_csv):
    df = load_transactions(small_fraud_csv)
    assert len(df) == 8000
    assert 0.005 < df["is_fraud"].mean() < 0.05


def test_leaky_column_is_never_a_feature():
    assert "chargeback_filed" in EXCLUDED
    assert "chargeback_filed" not in NUMERIC_FEATURES


def test_stratified_split_keeps_fraud_rate(small_fraud_csv):
    s = split(load_transactions(small_fraud_csv))
    assert abs(s.y_train.mean() - s.y_test.mean()) < 0.005


def test_accuracy_paradox(small_fraud_csv):
    """The lazy baseline gets ~98.5% accuracy while catching zero frauds."""
    s = split(load_transactions(small_fraud_csv))
    m = evaluate(s.y_test, build_baseline().fit(s.X_train, s.y_train).predict(s.X_test))
    assert m.accuracy > 0.95
    assert m.recall == 0.0
    assert m.true_positives == 0


def test_lower_threshold_catches_more_fraud(small_fraud_csv):
    s = split(load_transactions(small_fraud_csv))
    model = build_model().fit(s.X_train, s.y_train)
    at_050 = evaluate(s.y_test, predict_with_threshold(model, s.X_test, 0.5))
    at_010 = evaluate(s.y_test, predict_with_threshold(model, s.X_test, 0.1))
    assert at_010.recall >= at_050.recall
    assert at_010.false_positives >= at_050.false_positives


def test_unlimited_tree_overfits(small_fraud_csv):
    s = split(load_transactions(small_fraud_csv))
    rows = {str(r["max_depth"]): r for r in overfitting_demo(s, depths=(3, None))}
    deep = rows["unlimited"]
    assert deep["train_recall"] == 1.0
    assert deep["test_recall"] < deep["train_recall"]
