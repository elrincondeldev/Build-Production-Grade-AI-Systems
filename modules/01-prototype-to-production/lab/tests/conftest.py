"""Shared fixtures. Tests run offline: fake LLM, mocked HTTP, a small generated dataset."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from kestrel_fraud.adapters.faults import FaultInjectingTransport
from kestrel_fraud.adapters.llm import FakeLLM
from kestrel_fraud.config import Settings
from kestrel_fraud.main import create_app
from kestrel_fraud.training import find_repo_root, train

VALID_TXN = {
    "transaction_id": "txn_test_001",
    "customer_id": "cus_00017",
    "amount": 249.99,
    "merchant_category": "electronics",
    "hour": 2,
    "is_online": True,
    "country_mismatch": True,
    "card_age_days": 12,
    "device_is_new": True,
    "distance_from_home_km": 912.4,
    "txn_count_24h": 6,
    "avg_amount_30d": 41.5,
}


@pytest.fixture(scope="session")
def dataset(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("data") / "transactions.csv"
    generator = find_repo_root() / "datasets" / "fraud" / "generate.py"
    subprocess.run([sys.executable, str(generator), "--rows", "6000", "--seed", "7", "--out", str(out)], check=True)
    return out


@pytest.fixture(scope="session")
def trained_model_dir(dataset, tmp_path_factory) -> Path:
    """A model directory with one trained version and a LATEST pointer."""
    out = tmp_path_factory.mktemp("artifacts") / "fraud-model"
    train(dataset, out, version="test-v1")
    return out


@pytest.fixture
def model_dir(trained_model_dir, tmp_path) -> Path:
    """A private copy per test, so tests that tamper with files don't affect others."""
    dst = tmp_path / "fraud-model"
    shutil.copytree(trained_model_dir, dst)
    return dst


def make_settings(model_dir: Path, **overrides) -> Settings:
    base = dict(model_dir=model_dir, environment="test", log_json=True, enrichment_base_url=None)
    base.update(overrides)
    return Settings(_env_file=None, **base)


@pytest.fixture
def client(model_dir):
    app = create_app(make_settings(model_dir), llm=FakeLLM())
    with TestClient(app) as c:  # the context manager runs startup/shutdown (lifespan)
        yield c


def feature_store_transport(fail_first: int = 0, status_code: int = 503, timeout: bool = False):
    """An in-memory feature store wrapped in deterministic fault injection."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"txn_count_24h": 3, "avg_amount_30d": 52.0})

    return FaultInjectingTransport(
        httpx.MockTransport(handler), fail_first=fail_first, status_code=status_code, timeout=timeout
    )
