"""Smoke test for Track A: small data, fast. The full runs live in scripts/."""

from sklearn.metrics import roc_auc_score

from kestrel_fraud.data import FEATURES, LABEL, LEAKY_COLUMNS, load_transactions, time_split
from kestrel_fraud.model import train


def test_model_trains_without_leaky_columns():
    df = load_transactions(rows=20_000, seed=3)
    train_df, test_df = time_split(df)
    assert not set(LEAKY_COLUMNS) & set(FEATURES)
    assert train_df["timestamp"].max() <= test_df["timestamp"].min()  # no future in training
    model = train(train_df)
    scores = model.predict_proba(test_df[FEATURES])[:, 1]
    assert roc_auc_score(test_df[LABEL], scores) > 0.65
