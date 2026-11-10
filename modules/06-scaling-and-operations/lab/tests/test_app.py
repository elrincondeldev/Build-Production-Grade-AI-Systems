from fastapi.testclient import TestClient

from kestrel_platform.config import Settings
from kestrel_platform.main import create_app

PAYLOAD = {"amount": 900.0, "merchant_category": "crypto_exchange", "hour": 3, "is_online": True,
           "country_mismatch": True, "device_is_new": True, "avg_amount_30d": 30.0}


def test_health_ready_and_score() -> None:
    client = TestClient(create_app(Settings(app_version="v9")))
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/ready").status_code == 200
    r = client.post("/v1/score", json=PAYLOAD)
    assert r.status_code == 200
    body = r.json()
    assert body["model_version"] == "v9" and body["decision"] == "decline"
    assert r.headers["x-app-version"] == "v9"


def test_low_risk_is_approved() -> None:
    client = TestClient(create_app(Settings()))
    body = client.post("/v1/score", json={"amount": 12, "merchant_category": "grocery", "hour": 12}).json()
    assert body["decision"] == "approve"


def test_not_ready_returns_503() -> None:
    client = TestClient(create_app(Settings(ready=False)))
    assert client.get("/ready").status_code == 503
    assert client.get("/health").status_code == 200  # alive but not ready: no restart, no traffic


def test_fault_injection_returns_500() -> None:
    client = TestClient(create_app(Settings(fault_error_rate=1.0)))
    assert client.post("/v1/score", json=PAYLOAD).status_code == 500


def test_metrics_endpoint_exposes_request_counter() -> None:
    client = TestClient(create_app(Settings(app_version="metrics-test")))
    client.post("/v1/score", json=PAYLOAD)
    text = client.get("/metrics").text
    assert "kestrel_requests_total" in text and 'version="metrics-test"' in text


def test_validation_rejects_bad_input() -> None:
    client = TestClient(create_app(Settings()))
    assert client.post("/v1/score", json={"amount": -5, "merchant_category": "x", "hour": 99}).status_code == 422
