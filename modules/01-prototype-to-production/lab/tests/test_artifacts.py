import json

import pytest
from fastapi.testclient import TestClient

from kestrel_fraud.adapters.artifacts import (
    ArtifactIncompatible,
    ArtifactIntegrityError,
    ArtifactNotFound,
    load_artifact,
    sha256_file,
)
from kestrel_fraud.adapters.llm import FakeLLM
from kestrel_fraud.main import create_app

from .conftest import make_settings


def test_metadata_is_complete(model_dir):
    meta = json.loads((model_dir / "test-v1" / "metadata.json").read_text())
    for key in ("version", "model_sha256", "features", "data", "metrics", "code", "environment", "created_at"):
        assert key in meta
    assert "chargeback_filed" not in meta["features"]
    assert meta["model_sha256"] == sha256_file(model_dir / "test-v1" / "model.joblib")
    assert meta["metrics"]["pr_auc"] > meta["metrics"]["test_base_rate"]  # better than random


def test_latest_pointer_resolves(model_dir):
    assert load_artifact(model_dir, "latest").version == "test-v1"


def test_checksum_mismatch_is_detected(model_dir):
    with (model_dir / "test-v1" / "model.joblib").open("ab") as fh:
        fh.write(b"tampered")
    with pytest.raises(ArtifactIntegrityError):
        load_artifact(model_dir)


def test_feature_contract_mismatch_is_detected(model_dir):
    meta_path = model_dir / "test-v1" / "metadata.json"
    meta = json.loads(meta_path.read_text())
    meta["features"] = meta["features"][:-1]
    meta_path.write_text(json.dumps(meta))
    with pytest.raises(ArtifactIncompatible):
        load_artifact(model_dir)


def test_missing_version_raises(model_dir):
    with pytest.raises(ArtifactNotFound):
        load_artifact(model_dir, "does-not-exist")


def test_tampered_artifact_means_not_ready_but_alive(model_dir):
    with (model_dir / "test-v1" / "model.joblib").open("ab") as fh:
        fh.write(b"tampered")
    with TestClient(create_app(make_settings(model_dir), llm=FakeLLM())) as client:
        assert client.get("/health").status_code == 200  # liveness: process is fine
        ready = client.get("/ready")
        assert ready.status_code == 503  # readiness: do not send me traffic
        assert "ArtifactIntegrityError" in ready.json()["reason"]


def test_ready_when_artifact_verified(client):
    resp = client.get("/ready")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ready", "model_version": "test-v1", "reason": None}
