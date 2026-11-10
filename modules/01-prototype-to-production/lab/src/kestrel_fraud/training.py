"""Train the fraud model and write a versioned, checksummed artifact (📖 lessons 1.1 and 1.5).

This is Sam's notebook turned into a repeatable job:

* fixed seeds → the same data and model every run
* the SAME feature function as the API (``build_feature_vector``) → no skew
* a time-based split → the test set is "the future", like production
* an artifact folder with ``metadata.json``: the handoff contract between
  the person who trains and the service that serves

Usage:
    uv run python scripts/train.py                  # generate data if needed, train, write artifact
    uv run python scripts/train.py --rows 20000     # smaller/faster
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import sklearn
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

from .adapters.artifacts import LATEST_POINTER, METADATA_FILENAME, MODEL_FILENAME, sha256_file
from .config import LAB_ROOT
from .domain.features import (
    FEATURE_NAMES,
    FEATURE_SPEC_VERSION,
    FORBIDDEN_COLUMNS,
    build_feature_vector,
    transaction_from_csv_row,
)

SEED = 42


def find_repo_root(start: Path = LAB_ROOT) -> Path:
    """Walk up until we find the shared datasets folder (or use KESTREL_DATA_DIR)."""
    if env := os.environ.get("KESTREL_DATA_DIR"):
        return Path(env).resolve().parents[0]
    for parent in [start, *start.parents]:
        if (parent / "datasets" / "fraud" / "generate.py").exists():
            return parent
    raise FileNotFoundError("could not find datasets/fraud/generate.py above " + str(start))


def ensure_dataset(path: Path, rows: int, seed: int) -> None:
    if path.exists():
        return
    generator = find_repo_root() / "datasets" / "fraud" / "generate.py"
    print(f"dataset not found, generating it with {generator.name} (seed={seed}) …")
    subprocess.run(
        [sys.executable, str(generator), "--rows", str(rows), "--seed", str(seed), "--out", str(path)], check=True
    )


def file_digest(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def git_info(cwd: Path) -> dict[str, object]:
    def run(*args: str) -> str | None:
        try:
            out = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            return None
        return out.stdout.strip() if out.returncode == 0 else None

    commit = run("rev-parse", "HEAD")
    dirty = run("status", "--porcelain")
    return {"commit": commit or "unknown", "dirty": bool(dirty) if dirty is not None else None}


def load_xy(path: Path) -> tuple[np.ndarray, np.ndarray, list[str]]:
    with path.open() as fh:
        reader = csv.DictReader(fh)
        rows = sorted(reader, key=lambda r: r["timestamp"])  # time order for a realistic split
    # transaction_from_csv_row only reads allowed columns; FORBIDDEN_COLUMNS such as
    # chargeback_filed are present in the CSV but never touched. A test enforces this.
    X =np.array([build_feature_vector(transaction_from_csv_row(r)) for r in rows], dtype=np.float64)
    y = np.array([int(r["is_fraud"]) for r in rows], dtype=np.int64)
    return X, y, [r["timestamp"] for r in rows]


def train(data_path: Path, out_dir: Path, *, version: str | None = None, seed: int = SEED) -> Path:
    """Train, evaluate and write one artifact version. Returns the version directory."""
    t0 = time.perf_counter()
    X, y, timestamps = load_xy(data_path)
    split = int(len(y) * 0.8)  # first 80% (oldest) to train, last 20% (newest) to test
    X_train, X_test, y_train, y_test = X[:split], X[split:], y[:split], y[split:]

    model = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.08, max_leaf_nodes=31, random_state=seed)
    model.fit(X_train, y_train)
    proba = model.predict_proba(X_test)[:, 1]

    metrics = {
        "roc_auc": round(float(roc_auc_score(y_test, proba)), 4),
        "pr_auc": round(float(average_precision_score(y_test, proba)), 4),
        "brier": round(float(brier_score_loss(y_test, proba)), 5),
        "test_base_rate": round(float(y_test.mean()), 4),
        "n_train": int(len(y_train)),
        "n_test": int(len(y_test)),
    }

    data_digest = file_digest(data_path)
    created = datetime.now(timezone.utc)
    version = version or f"{created:%Y%m%dT%H%M%SZ}-{data_digest[:8]}"
    vdir = out_dir / version
    vdir.mkdir(parents=True, exist_ok=False)  # never overwrite an existing version

    joblib.dump(model, vdir / MODEL_FILENAME)
    metadata = {
        "name": "fraud-model",
        "version": version,
        "created_at": created.isoformat(timespec="seconds"),
        "model_file": MODEL_FILENAME,
        "model_sha256": sha256_file(vdir / MODEL_FILENAME),
        "model_class": f"{type(model).__module__}.{type(model).__name__}",
        "hyperparameters": {k: v for k, v in model.get_params().items() if v is None or isinstance(v, (int, float, str, bool))},
        "feature_spec_version": FEATURE_SPEC_VERSION,
        "features": list(FEATURE_NAMES),
        "excluded_columns": sorted(FORBIDDEN_COLUMNS),
        "data": {
            "path": data_path.name,
            "sha256": data_digest,
            "rows": int(len(y)),
            "time_range": [timestamps[0], timestamps[-1]],
            "split": "time-based 80/20",
        },
        "metrics": metrics,
        "code": git_info(LAB_ROOT),
        "environment": {
            "python": platform.python_version(),
            "sklearn": sklearn.__version__,
            "numpy": np.__version__,
            "platform": platform.platform(),
        },
        "seed": seed,
        "training_seconds": round(time.perf_counter() - t0, 2),
    }
    (vdir / METADATA_FILENAME).write_text(json.dumps(metadata, indent=2) + "\n")

    # Atomically move the LATEST pointer: write a temp file, then rename (rename is atomic on POSIX).
    tmp = out_dir / f".{LATEST_POINTER}.tmp"
    tmp.write_text(version + "\n")
    tmp.replace(out_dir / LATEST_POINTER)
    return vdir


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Train the Kestrel fraud model and write a versioned artifact")
    default_data = find_repo_root() / "datasets" / "fraud" / "transactions.csv"
    parser.add_argument("--data", type=Path, default=default_data)
    parser.add_argument("--rows", type=int, default=50_000, help="rows to generate if the dataset is missing")
    parser.add_argument("--out", type=Path, default=LAB_ROOT / "artifacts" / "fraud-model")
    parser.add_argument("--version", default=None, help="defaults to <UTC timestamp>-<data sha256 prefix>")
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args(argv)

    ensure_dataset(args.data, args.rows, args.seed)
    vdir = train(args.data, args.out, version=args.version, seed=args.seed)
    meta = json.loads((vdir / METADATA_FILENAME).read_text())
    print(f"✅ wrote artifact {vdir}")
    print(f"   sha256   {meta['model_sha256']}")
    print(f"   metrics  {json.dumps(meta['metrics'])}")


if __name__ == "__main__":
    main()
