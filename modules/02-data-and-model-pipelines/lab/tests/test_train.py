import mlflow
from mlflow.tracking import MlflowClient

from pipelines.train import MODEL_NAME, run


def test_tracked_training_run_registers_a_versioned_model(tmp_path, monkeypatch):
    monkeypatch.setenv("KESTREL_LAB_DATA_DIR", str(tmp_path / "data"))
    uri = f"sqlite:///{tmp_path / 'mlflow.db'}"
    result = run(rows=3_000, seed=1, trials=2, tracking_uri=uri, experiment="test")

    assert 0.0 <= result.test_pr_auc <= 1.0
    assert result.promoted_to_champion  # first model always becomes champion

    client = MlflowClient(tracking_uri=uri)
    run_data = client.get_run(result.run_id).data
    for tag in ("raw_file_sha256", "validated_data_sha256", "git_commit", "uv_lock_sha256"):
        assert tag in run_data.tags, f"missing lineage tag {tag}"
    assert str(client.get_model_version_by_alias(MODEL_NAME, "champion").version) == result.model_version

    mlflow.set_tracking_uri(uri)
    model = mlflow.sklearn.load_model(f"models:/{MODEL_NAME}@champion")
    assert hasattr(model, "predict_proba")
