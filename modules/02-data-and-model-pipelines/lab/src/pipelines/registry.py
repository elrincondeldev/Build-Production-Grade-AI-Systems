"""Load a model from the registry by *alias*, the way a serving service would. 📖 Lesson 2.6.

    uv run python -m pipelines.registry            # list versions and aliases
    uv run python -m pipelines.registry --score    # load @champion and score 5 rows
"""

from __future__ import annotations

import argparse

import mlflow
from mlflow.tracking import MlflowClient

from pipelines.data import generate_raw, load_raw
from pipelines.train import MODEL_NAME, default_tracking_uri
from pipelines.validate import feature_columns, gate


def load_champion(tracking_uri: str | None = None):
    mlflow.set_tracking_uri(tracking_uri or default_tracking_uri())
    # Serving code asks for "@champion", never for "version 7". Promotion and
    # rollback then become a registry operation, not a redeploy.
    return mlflow.sklearn.load_model(f"models:/{MODEL_NAME}@champion")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--score", action="store_true")
    args = parser.parse_args()
    mlflow.set_tracking_uri(default_tracking_uri())
    client = MlflowClient()
    alias_map: dict[str, list[str]] = {}
    for alias, version in client.get_registered_model(MODEL_NAME).aliases.items():
        alias_map.setdefault(str(version), []).append(alias)
    for mv in sorted(client.search_model_versions(f"name='{MODEL_NAME}'"), key=lambda m: int(m.version)):
        aliases = ",".join(sorted(alias_map.get(str(mv.version), []))) or "-"
        pr_auc = client.get_run(mv.run_id).data.metrics.get("test_pr_auc", float("nan"))
        print(f"v{mv.version:<3} aliases={aliases:<22} test_pr_auc={pr_auc:.3f} run={mv.run_id[:8]}")
    if args.score:
        model = load_champion()
        df = gate(load_raw(generate_raw()))
        print(model.predict_proba(df[feature_columns()].head(5))[:, 1].round(4))


if __name__ == "__main__":
    main()
