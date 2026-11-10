"""Train your first fraud model and see why accuracy lies.

📖 See lesson 0.4 "Machine learning in one hour".
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier

NUMERIC_FEATURES = [
    "amount",
    "hour",
    "is_online",
    "country_mismatch",
    "card_age_days",
    "txn_count_24h",
    "avg_amount_30d",
    "device_is_new",
    "distance_from_home_km",
]
CATEGORICAL_FEATURES = ["merchant_category"]
LABEL = "is_fraud"

# Columns we deliberately do NOT use as features:
# - IDs and timestamps: unique per row, they let a model memorise instead of learn.
# - chargeback_filed: only known AFTER the label exists -> data leakage (lesson 2.2).
EXCLUDED = ["transaction_id", "timestamp", "customer_id", "country", "chargeback_filed"]


@dataclass(frozen=True)
class Split:
    X_train: pd.DataFrame
    X_test: pd.DataFrame
    y_train: pd.Series
    y_test: pd.Series


@dataclass(frozen=True)
class Metrics:
    accuracy: float
    precision: float
    recall: float
    true_negatives: int
    false_positives: int
    false_negatives: int
    true_positives: int

    @property
    def frauds_in_test(self) -> int:
        return self.true_positives + self.false_negatives


def load_transactions(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = set(NUMERIC_FEATURES + CATEGORICAL_FEATURES + [LABEL]) - set(df.columns)
    if missing:
        raise ValueError(f"CSV is missing columns: {sorted(missing)}")
    return df


def split(df: pd.DataFrame, test_size: float = 0.2, seed: int = 42) -> Split:
    """Stratified split: keeps the ~1.4% fraud rate equal in train and test.

    Without stratify=..., a small test set could end up with almost no frauds
    and every metric would be noise.
    """
    X = df[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    y = df[LABEL]
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=test_size, random_state=seed, stratify=y)
    return Split(X_tr, X_te, y_tr, y_te)


def build_model() -> Pipeline:
    """Preprocessing + model in ONE object, so serving can never forget a step.

    Fitting the scaler inside the pipeline also means it only ever sees training
    data (fitting it on all data first is a subtle form of leakage).
    """
    preprocess = ColumnTransformer(
        [
            ("num", StandardScaler(), NUMERIC_FEATURES),
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
        ]
    )
    return Pipeline([("preprocess", preprocess), ("clf", LogisticRegression(max_iter=1000))])


def build_baseline() -> DummyClassifier:
    """The 'lazy' model: always predicts the most common class (not fraud)."""
    return DummyClassifier(strategy="most_frequent")


def evaluate(y_true: pd.Series, y_pred) -> Metrics:
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return Metrics(
        accuracy=float(accuracy_score(y_true, y_pred)),
        precision=float(precision_score(y_true, y_pred, zero_division=0)),
        recall=float(recall_score(y_true, y_pred, zero_division=0)),
        true_negatives=int(tn),
        false_positives=int(fp),
        false_negatives=int(fn),
        true_positives=int(tp),
    )


def predict_with_threshold(model: Pipeline, X: pd.DataFrame, threshold: float):
    """`model.predict` silently uses 0.5. Choosing the threshold is a *business* decision."""
    return (model.predict_proba(X)[:, 1] >= threshold).astype(int)


def overfitting_demo(s: Split, depths: tuple[int | None, ...] = (3, 6, None)) -> list[dict]:
    """Train decision trees of growing depth; compare train vs test recall/precision.

    A tree with unlimited depth (None) can memorise the training set perfectly
    and still do much worse on data it has never seen. That gap is overfitting.
    """
    rows = []
    X_train = pd.get_dummies(s.X_train, columns=CATEGORICAL_FEATURES)
    X_test = pd.get_dummies(s.X_test, columns=CATEGORICAL_FEATURES).reindex(columns=X_train.columns, fill_value=0)
    for depth in depths:
        tree = DecisionTreeClassifier(max_depth=depth, random_state=42).fit(X_train, s.y_train)
        train_m = evaluate(s.y_train, tree.predict(X_train))
        test_m = evaluate(s.y_test, tree.predict(X_test))
        rows.append(
            {
                "max_depth": "unlimited" if depth is None else depth,
                "train_recall": train_m.recall,
                "test_recall": test_m.recall,
                "train_precision": train_m.precision,
                "test_precision": test_m.precision,
            }
        )
    return rows
