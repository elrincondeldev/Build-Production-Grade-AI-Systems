"""The fraud model Sam handed over, reproduced as a scikit-learn Pipeline.

Note ``class_weight="balanced"``: a popular way to "fix" class imbalance that
inflates predicted probabilities. Ranking (ROC/PR-AUC) stays fine, but the
scores stop meaning "probability of fraud". Lesson 4.2 measures and fixes it.
"""

from __future__ import annotations

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from kestrel_fraud.data import CATEGORICAL_FEATURES, FEATURES, LABEL, NUMERIC_FEATURES


def make_model(class_weight: str | None = "balanced", seed: int = 0) -> Pipeline:
    pre = ColumnTransformer(
        [
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
            ("num", "passthrough", NUMERIC_FEATURES),
        ]
    )
    clf = HistGradientBoostingClassifier(
        max_iter=200, learning_rate=0.05, max_leaf_nodes=31, class_weight=class_weight, random_state=seed
    )
    return Pipeline([("pre", pre), ("clf", clf)])


def train(df: pd.DataFrame, class_weight: str | None = "balanced", seed: int = 0) -> Pipeline:
    model = make_model(class_weight=class_weight, seed=seed)
    model.fit(df[FEATURES], df[LABEL])
    return model
