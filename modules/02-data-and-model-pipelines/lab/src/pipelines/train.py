"""Reproducible, tracked training run for the fraud model. 📖 Lesson 2.6.

    uv run python -m pipelines.train --rows 20000 --trials 10

What one run does, in order:
  1. ingest   → generate (or reuse) the raw CSV for (rows, seed)
  2. validate → the gate from lesson 2.1 (stops the run on bad data)
  3. leakage  → contract + statistical check from lesson 2.2
  4. split    → *temporal* train / validation / test (70 / 15 / 15)
  5. tune     → Optuna searches hyperparameters on the validation set
  6. refit    → best params on train+validation, final score on the untouched test set
  7. track    → MLflow: params, metrics, data digests, git commit, env lock hash, model
  8. register → new model version gets alias `challenger`; becomes `champion` if it beats the current one
"""

from __future__ import annotations

import argparse
import json
import tempfile
import warnings
from dataclasses import dataclass
from pathlib import Path

import mlflow
import optuna
import pandas as pd
from mlflow.models import infer_signature
from mlflow.tracking import MlflowClient
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from pipelines.data import generate_raw, load_raw
from pipelines.digest import dataframe_sha256, file_sha256, git_state
from pipelines.leakage import assert_no_leakage
from pipelines.paths import LAB_DIR
from pipelines.validate import feature_columns, gate

MODEL_NAME = "fraud-classifier"
LABEL = "is_fraud"
CATEGORICAL = ["merchant_category"]
TRUSTED_TYPES = ["sklearn.ensemble._hist_gradient_boosting.predictor.TreePredictor"]


@dataclass
class RunResult:
    run_id: str
    model_version: str
    test_pr_auc: float
    test_roc_auc: float
    promoted_to_champion: bool
    best_params: dict


def default_tracking_uri() -> str:
    return f"sqlite:///{LAB_DIR / 'mlflow.db'}"


def temporal_split(df: pd.DataFrame, train: float = 0.70, val: float = 0.15) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split by time, never randomly, for event data. 📖 Lesson 2.2 (leakage through time).

    A random split lets the model 'see the future' (e.g. the same fraud ring on both
    sides), which inflates offline scores that then collapse in production.
    """
    df = df.sort_values("timestamp").reset_index(drop=True)
    a, b = int(len(df) * train), int(len(df) * (train + val))
    return df.iloc[:a], df.iloc[a:b], df.iloc[b:]


def build_model(features: list[str], params: dict, seed: int) -> Pipeline:
    numeric = [f for f in features if f not in CATEGORICAL]
    pre = ColumnTransformer(
        [("cat", OneHotEncoder(handle_unknown="ignore"), [f for f in features if f in CATEGORICAL]),
         ("num", "passthrough", numeric)]
    )
    clf = HistGradientBoostingClassifier(random_state=seed, **params)
    return Pipeline([("pre", pre), ("clf", clf)])


def _score(model: Pipeline, df: pd.DataFrame, features: list[str]) -> tuple[float, float]:
    p = model.predict_proba(df[features])[:, 1]
    return float(average_precision_score(df[LABEL], p)), float(roc_auc_score(df[LABEL], p))


def _champion_score(client: MlflowClient) -> float | None:
    try:
        mv = client.get_model_version_by_alias(MODEL_NAME, "champion")
    except Exception:  # no registered model or no champion alias yet
        return None
    run = client.get_run(mv.run_id)
    return run.data.metrics.get("test_pr_auc")


def run(
    rows: int = 20_000,
    seed: int = 42,
    trials: int = 10,
    tracking_uri: str | None = None,
    experiment: str = "fraud-classifier",
    features: list[str] | None = None,
    skip_leakage_check: bool = False,
) -> RunResult:
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    # MLflow hints that integer columns can't hold NaN; our validation gate already forbids nulls.
    warnings.filterwarnings("ignore", message=".*Inferred schema contains integer.*")
    tracking_uri = tracking_uri or default_tracking_uri()
    mlflow.set_tracking_uri(tracking_uri)
    if mlflow.get_experiment_by_name(experiment) is None:
        artifact_root = Path(tracking_uri.removeprefix("sqlite:///")).parent / "mlartifacts"
        mlflow.create_experiment(experiment, artifact_location=artifact_root.resolve().as_uri())
    mlflow.set_experiment(experiment)

    # 1–2. ingest + validate
    raw_path = generate_raw(rows=rows, seed=seed)
    df = gate(load_raw(raw_path))

    # 3. leakage
    features = features or feature_columns()
    if not skip_leakage_check:
        assert_no_leakage(df, features)

    # 4. split
    train_df, val_df, test_df = temporal_split(df)

    # 5. tune
    def objective(trial: optuna.Trial) -> float:
        params = {
            "learning_rate": trial.suggest_float("learning_rate", 0.02, 0.3, log=True),
            "max_depth": trial.suggest_int("max_depth", 2, 8),
            "max_iter": trial.suggest_int("max_iter", 50, 300, step=50),
            "l2_regularization": trial.suggest_float("l2_regularization", 1e-3, 10.0, log=True),
        }
        with mlflow.start_run(run_name=f"trial-{trial.number}", nested=True):
            model = build_model(features, params, seed).fit(train_df[features], train_df[LABEL])
            pr_auc, _ = _score(model, val_df, features)
            mlflow.log_params(params)
            mlflow.log_metric("val_pr_auc", pr_auc)
        return pr_auc

    with mlflow.start_run(run_name=f"train-rows{rows}-seed{seed}") as parent:
        study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=seed))
        study.optimize(objective, n_trials=trials)

        # 6. refit on train+val, evaluate once on test
        fit_df = pd.concat([train_df, val_df])
        model = build_model(features, study.best_params, seed).fit(fit_df[features], fit_df[LABEL])
        test_pr_auc, test_roc_auc = _score(model, test_df, features)

        # 7. track everything needed to rebuild this exact model
        lock = LAB_DIR / "uv.lock"
        mlflow.log_params({**study.best_params, "rows": rows, "seed": seed, "trials": trials, "features": ",".join(features)})
        mlflow.log_metrics({
            "best_val_pr_auc": study.best_value,
            "test_pr_auc": test_pr_auc,
            "test_roc_auc": test_roc_auc,
            "test_base_rate": float(test_df[LABEL].mean()),
        })
        lineage = {
            "raw_file": raw_path.name,
            "raw_file_sha256": file_sha256(raw_path),
            "validated_data_sha256": dataframe_sha256(df),
            "generator": {"script": "datasets/fraud/generate.py", "rows": rows, "seed": seed, "scenario": "baseline"},
            "split": {"train": len(train_df), "val": len(val_df), "test": len(test_df), "method": "temporal 70/15/15"},
            "uv_lock_sha256": file_sha256(lock) if lock.exists() else "missing",
            **git_state(LAB_DIR),
        }
        mlflow.set_tags({k: str(v) for k, v in lineage.items() if not isinstance(v, dict)})
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "lineage.json"
            p.write_text(json.dumps(lineage, indent=2))
            mlflow.log_artifact(str(p))

        # 8. register
        sample = test_df[features].head(5)
        info = mlflow.sklearn.log_model(
            model,
            name="model",
            signature=infer_signature(sample, model.predict_proba(sample)[:, 1]),
            input_example=sample,
            registered_model_name=MODEL_NAME,
            # MLflow saves sklearn models with skops instead of pickle: loading a pickle
            # can execute arbitrary code. We explicitly trust the one type we reviewed.
            skops_trusted_types=TRUSTED_TYPES,
        )
        version = str(info.registered_model_version)
        client = MlflowClient()
        client.set_registered_model_alias(MODEL_NAME, "challenger", version)
        champion = _champion_score(client)
        promoted = champion is None or test_pr_auc > champion
        if promoted:
            client.set_registered_model_alias(MODEL_NAME, "champion", version)
        mlflow.set_tag("promoted_to_champion", str(promoted))

    return RunResult(parent.info.run_id, version, test_pr_auc, test_roc_auc, promoted, study.best_params)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rows", type=int, default=20_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--trials", type=int, default=10)
    parser.add_argument("--features", type=str, default=None, help="comma-separated override (try adding chargeback_filed!)")
    parser.add_argument("--skip-leakage-check", action="store_true", help="⚠️ for the 'Break it' exercise only")
    args = parser.parse_args()
    result = run(
        rows=args.rows, seed=args.seed, trials=args.trials,
        features=args.features.split(",") if args.features else None,
        skip_leakage_check=args.skip_leakage_check,
    )
    print(f"run_id={result.run_id}")
    print(f"registered {MODEL_NAME} v{result.model_version}  test PR-AUC={result.test_pr_auc:.3f}  ROC-AUC={result.test_roc_auc:.3f}")
    print(f"best params: {result.best_params}")
    print("promoted to @champion ✅" if result.promoted_to_champion else "kept as @challenger (did not beat champion)")
    print("Browse runs:  uv run mlflow ui --backend-store-uri sqlite:///mlflow.db  → http://127.0.0.1:5000")


if __name__ == "__main__":
    main()
