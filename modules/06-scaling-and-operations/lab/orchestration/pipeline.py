"""The fraud training pipeline: ingest -> validate -> train -> evaluate -> register.

Run it:
    uv run python -m orchestration.pipeline --rows 20000

📖 Lesson 6.2. The same five functions are wrapped as a Prefect flow in
`prefect_flow.py`, which shows that the business logic does not change when you
swap orchestrators. Only the wrapper does.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestration.dag import DAG

LEAKY_COLUMNS = {"chargeback_filed"}  # known only after the label exists (lesson 2.2)
ID_COLUMNS = {"transaction_id", "timestamp", "customer_id", "country"}
LABEL = "is_fraud"
# Quality gate. PR-AUC must be judged against the base rate: a random model scores
# PR-AUC ~= fraud rate (~1.4%). On this deliberately noisy synthetic data even the
# perfect (ground-truth) model only reaches ~0.10, so we require a 3x lift.
MIN_LIFT_OVER_BASE_RATE = 3.0


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "datasets" / "fraud" / "generate.py").exists():
            return parent
    raise FileNotFoundError("course repo root not found")


def ingest(workdir: Path, rows: int, seed: int) -> Path:
    out = workdir / "raw" / "transactions.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    generator = _repo_root() / "datasets" / "fraud" / "generate.py"
    subprocess.run(
        [sys.executable, str(generator), "--rows", str(rows), "--seed", str(seed), "--out", str(out)],
        check=True,
        capture_output=True,
    )
    return out


def validate(path: Path) -> list[dict[str, Any]]:
    with path.open() as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        raise ValueError("no rows ingested")
    required = {"amount", "merchant_category", "hour", LABEL}
    missing = required - set(rows[0])
    if missing:
        raise ValueError(f"schema check failed, missing columns {sorted(missing)}")
    fraud_rate = sum(int(r[LABEL]) for r in rows) / len(rows)
    if not 0.002 <= fraud_rate <= 0.10:
        raise ValueError(f"fraud rate {fraud_rate:.2%} outside the expected 0.2%-10% band")
    if any(float(r["amount"]) <= 0 for r in rows):
        raise ValueError("non-positive amounts found")
    return rows


def _features(row: dict[str, Any]) -> dict[str, Any]:
    feats: dict[str, Any] = {}
    for key, value in row.items():
        if key in LEAKY_COLUMNS or key in ID_COLUMNS or key == LABEL:
            continue
        feats[key] = value if key == "merchant_category" else float(value)
    return feats


def train(rows: list[dict[str, Any]], seed: int) -> dict[str, Any]:
    from sklearn.feature_extraction import DictVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    X = [_features(r) for r in rows]
    y = [int(r[LABEL]) for r in rows]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, stratify=y, random_state=seed)
    model = make_pipeline(
        DictVectorizer(sparse=False), StandardScaler(), LogisticRegression(max_iter=1000, class_weight="balanced")
    )
    model.fit(X_train, y_train)
    return {"model": model, "X_test": X_test, "y_test": y_test}


def evaluate(trained: dict[str, Any]) -> dict[str, float]:
    from sklearn.metrics import average_precision_score, roc_auc_score

    scores = trained["model"].predict_proba(trained["X_test"])[:, 1]
    base_rate = sum(trained["y_test"]) / len(trained["y_test"])
    metrics = {
        "pr_auc": float(average_precision_score(trained["y_test"], scores)),
        "roc_auc": float(roc_auc_score(trained["y_test"], scores)),
        "base_rate": base_rate,
    }
    required = MIN_LIFT_OVER_BASE_RATE * base_rate
    if metrics["pr_auc"] < required:
        raise ValueError(f"quality gate failed: PR-AUC {metrics['pr_auc']:.3f} < {required:.3f} (3x base rate)")
    return metrics


def register(workdir: Path, trained: dict[str, Any], metrics: dict[str, float], data_path: Path) -> Path:
    import joblib

    version = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    target = workdir / "registry" / "fraud-model" / version
    target.mkdir(parents=True, exist_ok=True)
    artifact = target / "model.joblib"
    joblib.dump(trained["model"], artifact)
    meta = {
        "version": version,
        "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        "data_sha256": hashlib.sha256(data_path.read_bytes()).hexdigest(),
        "metrics": metrics,
        "stage": "staging",  # promotion to production is a separate, reviewed step
    }
    (target / "metadata.json").write_text(json.dumps(meta, indent=2))
    return target


def build_pipeline(workdir: Path, rows: int = 20_000, seed: int = 42) -> DAG:
    dag = DAG("fraud-training")

    @dag.task("ingest", retries=2)
    def _ingest(r: dict[str, Any]) -> Path:
        return ingest(workdir, rows, seed)

    @dag.task("validate", upstream=["ingest"])
    def _validate(r: dict[str, Any]) -> list[dict[str, Any]]:
        return validate(r["ingest"])

    @dag.task("train", upstream=["validate"])
    def _train(r: dict[str, Any]) -> dict[str, Any]:
        return train(r["validate"], seed)

    @dag.task("evaluate", upstream=["train"])
    def _evaluate(r: dict[str, Any]) -> dict[str, float]:
        return evaluate(r["train"])

    @dag.task("register", upstream=["train", "evaluate"])
    def _register(r: dict[str, Any]) -> Path:
        return register(workdir, r["train"], r["evaluate"], r["ingest"])

    return dag


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=20_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--workdir", type=Path, default=Path("artifacts/pipeline"))
    args = parser.parse_args()
    dag = build_pipeline(args.workdir, args.rows, args.seed)
    print(f"DAG '{dag.name}' order: {' -> '.join(dag.topological_order())}")
    runs = dag.run(verbose=True)
    if runs["register"].status == "success":
        print(f"registered: {dag.results['register']}  metrics: {dag.results['evaluate']}")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
