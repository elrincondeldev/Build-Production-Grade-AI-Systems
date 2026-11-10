from __future__ import annotations

import os

import pytest

os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")

from kestrel_docs.config import Settings  # noqa: E402
from kestrel_docs.service import Services, build_services  # noqa: E402
from pipelines.data import generate_raw, load_raw  # noqa: E402


@pytest.fixture(scope="session")
def raw_df(tmp_path_factory):
    path = generate_raw(rows=5_000, seed=7, out=tmp_path_factory.mktemp("data") / "raw.csv")
    return load_raw(path)


@pytest.fixture(scope="session")
def settings() -> Settings:
    # Explicit offline providers: tests must never touch the network.
    return Settings(llm_provider="fake", embeddings_provider="hash", reranker="lexical")


@pytest.fixture(scope="session")
def services(settings) -> Services:
    return build_services(settings)
