"""Runs only when the optional extra is installed:  uv sync --extra onnx"""

import numpy as np
import pytest

pytest.importorskip("skl2onnx")
ort = pytest.importorskip("onnxruntime")

import onnx_export  # noqa: E402  (scripts/ is on the pytest pythonpath)


def test_onnx_matches_sklearn(tmp_path, monkeypatch):
    monkeypatch.setattr(onnx_export, "ARTIFACTS", tmp_path)
    df = onnx_export.load_data(rows=4000)
    model, x_test = onnx_export.train(df)
    onnx_export.export(model, tmp_path / "m.onnx")
    session = ort.InferenceSession(str(tmp_path / "m.onnx"), providers=["CPUExecutionProvider"])
    onnx_proba = session.run(["probabilities"], {"features": x_test})[0][:, 1]
    assert np.max(np.abs(onnx_proba - model.predict_proba(x_test)[:, 1])) < 1e-4
