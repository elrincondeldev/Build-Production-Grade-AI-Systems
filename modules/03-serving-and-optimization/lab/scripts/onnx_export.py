"""Train the fraud model, export it to ONNX, and compare scikit-learn vs ONNX Runtime. 📖 Lesson 3.7.

    uv sync --extra onnx
    uv run python scripts/onnx_export.py

Steps: generate data -> train -> export -> verify parity -> benchmark -> write artifacts/.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split

from kestrel_serving.config import REPO_ROOT
from kestrel_serving.fraud_features import FEATURE_NAMES, encode
from kestrel_serving.stats import summarize

ARTIFACTS = Path(__file__).resolve().parents[1] / "artifacts"


def load_data(rows: int = 20_000) -> pd.DataFrame:
    out = ARTIFACTS / "transactions.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [sys.executable, str(REPO_ROOT / "datasets" / "fraud" / "generate.py"), "--rows", str(rows), "--out", str(out)],
        check=True,
    )
    return pd.read_csv(out)


def train(df: pd.DataFrame) -> tuple[GradientBoostingClassifier, np.ndarray]:
    x, y = encode(df), df["is_fraud"].to_numpy()
    x_train, x_test, y_train, _ = train_test_split(x, y, test_size=0.2, random_state=0, stratify=y)
    model = GradientBoostingClassifier(n_estimators=150, max_depth=3, random_state=0).fit(x_train, y_train)
    return model, x_test


def export(model: GradientBoostingClassifier, path: Path) -> bytes:
    from skl2onnx import to_onnx
    from skl2onnx.common.data_types import FloatTensorType

    onx = to_onnx(
        model,
        initial_types=[("features", FloatTensorType([None, len(FEATURE_NAMES)]))],
        options={id(model): {"zipmap": False}},  # plain probability tensor instead of a list of dicts
        target_opset=17,
    )
    data = onx.SerializeToString()
    path.write_bytes(data)
    return data


def bench(fn, x: np.ndarray, repeats: int) -> dict[str, float]:  # type: ignore[no-untyped-def]
    for _ in range(10):  # warm-up
        fn(x)
    times = []
    for _ in range(repeats):
        start = time.perf_counter()
        fn(x)
        times.append((time.perf_counter() - start) * 1000)
    return summarize(times)


def main() -> None:
    import onnxruntime as ort

    df = load_data()
    model, x_test = train(df)
    onnx_path = ARTIFACTS / "fraud_model.onnx"
    data = export(model, onnx_path)

    session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    sk_proba = model.predict_proba(x_test)[:, 1]
    ort_proba = session.run(["probabilities"], {"features": x_test})[0][:, 1]
    max_diff = float(np.max(np.abs(sk_proba - ort_proba)))
    print(f"parity: max |p_sklearn - p_onnx| over {len(x_test):,} rows = {max_diff:.2e}  ->  {'OK' if max_diff < 1e-4 else 'MISMATCH'}")

    single = x_test[:1]
    batch = x_test[:1000]
    rows = [
        ("scikit-learn", "1 row", bench(model.predict_proba, single, 300)),
        ("onnxruntime", "1 row", bench(lambda x: session.run(None, {"features": x}), single, 300)),
        ("scikit-learn", "1000 rows", bench(model.predict_proba, batch, 50)),
        ("onnxruntime", "1000 rows", bench(lambda x: session.run(None, {"features": x}), batch, 50)),
    ]
    print("\n| runtime | input | p50 ms | p95 ms |\n|---|---|---|---|")
    for runtime, size, s in rows:
        print(f"| {runtime} | {size} | {s['p50']:.3f} | {s['p95']:.3f} |")

    metadata = {
        "artifact": onnx_path.name,
        "sha256": hashlib.sha256(data).hexdigest(),
        "features": FEATURE_NAMES,
        "input_name": "features",
        "output_name": "probabilities",
        "opset": 17,
        "parity_max_abs_diff": max_diff,
    }
    (ARTIFACTS / "fraud_model.onnx.json").write_text(json.dumps(metadata, indent=2))
    print(f"\nwrote {onnx_path.relative_to(Path.cwd()) if onnx_path.is_relative_to(Path.cwd()) else onnx_path} "
          f"({len(data) / 1024:.0f} KiB) + metadata, sha256={metadata['sha256'][:12]}…")


if __name__ == "__main__":
    main()
