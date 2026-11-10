import json
import shutil

from fastapi.testclient import TestClient

from kestrel_fraud.adapters.llm import FakeLLM
from kestrel_fraud.main import create_app

from .conftest import VALID_TXN, feature_store_transport, make_settings


def test_score_happy_path(client):
    resp = client.post("/v1/score", json=VALID_TXN)
    assert resp.status_code == 200
    body = resp.json()
    assert 0 <= body["score"] <= 1
    assert body["source"] == "model" and body["model_version"] == "test-v1"
    assert body["decision"] in {"approve", "review", "decline"}
    assert body["degraded"] is False
    assert any("country" in r for r in body["reasons"])


def test_risky_transaction_scores_higher_than_boring_one(client):
    boring = {**VALID_TXN, "transaction_id": "t2", "merchant_category": "grocery", "hour": 14,
              "is_online": False, "country_mismatch": False, "device_is_new": False,
              "card_age_days": 900, "amount": 25.0, "distance_from_home_km": 2.0}
    risky = client.post("/v1/score", json=VALID_TXN).json()["score"]
    safe = client.post("/v1/score", json=boring).json()["score"]
    assert risky > safe


def test_schema_validation_returns_422(client):
    for bad in ({**VALID_TXN, "hour": 25}, {**VALID_TXN, "amount": -5},
                {**VALID_TXN, "merchant_category": "casino"}, {**VALID_TXN, "surprise": 1}):
        assert client.post("/v1/score", json=bad).status_code == 422
    missing = {k: v for k, v in VALID_TXN.items() if k != "amount"}
    assert client.post("/v1/score", json=missing).status_code == 422


def test_request_id_is_generated_and_returned(client):
    resp = client.get("/health")
    assert len(resp.headers["X-Request-ID"]) == 32


def test_request_id_is_preserved_and_in_body(client):
    resp = client.post("/v1/score", json=VALID_TXN, headers={"X-Request-ID": "abc-123"})
    assert resp.headers["X-Request-ID"] == "abc-123"
    assert resp.json()["request_id"] == "abc-123"


def test_malicious_request_id_is_replaced(client):
    resp = client.get("/health", headers={"X-Request-ID": "bad id\nwith newline"})
    assert resp.headers["X-Request-ID"] != "bad id\nwith newline"


def test_request_id_is_propagated_to_feature_store(model_dir):
    transport = feature_store_transport()
    app = create_app(make_settings(model_dir, enrichment_base_url="http://fs.test"),
                     enrichment_transport=transport, llm=FakeLLM())
    txn = {k: v for k, v in VALID_TXN.items() if k not in ("txn_count_24h", "avg_amount_30d")}
    with TestClient(app) as c:
        resp = c.post("/v1/score", json=txn, headers={"X-Request-ID": "trace-me-42"})
    assert resp.status_code == 200 and resp.json()["degraded"] is False
    assert transport.requests[0].headers["X-Request-ID"] == "trace-me-42"


def test_enrichment_outage_degrades_gracefully(model_dir):
    transport = feature_store_transport(fail_first=99)
    app = create_app(make_settings(model_dir, enrichment_base_url="http://fs.test", enrichment_deadline_s=0.5),
                     enrichment_transport=transport, llm=FakeLLM())
    txn = {k: v for k, v in VALID_TXN.items() if k not in ("txn_count_24h", "avg_amount_30d")}
    with TestClient(app) as c:
        resp = c.post("/v1/score", json=txn)
    assert resp.status_code == 200  # the payment flow is NOT blocked
    body = resp.json()
    assert body["degraded"] is True and "enrichment_unavailable" in body["degraded_reasons"]
    assert body["source"] == "model"


def test_missing_model_falls_back_to_rules(model_dir):
    shutil.rmtree(model_dir)
    with TestClient(create_app(make_settings(model_dir), llm=FakeLLM())) as c:
        assert c.get("/ready").status_code == 503
        resp = c.post("/v1/score", json=VALID_TXN)
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "rules" and body["model_version"] is None
    assert "model_unavailable" in body["degraded_reasons"]
    assert body["score"] > 0.5  # many risk signals fire for this transaction


def test_explain_streams_server_sent_events(client):
    client.post("/v1/score", json=VALID_TXN)
    with client.stream("GET", f"/v1/explain/{VALID_TXN['transaction_id']}") as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        text = "".join(resp.iter_text())
    data_lines = [line.removeprefix("data: ") for line in text.splitlines() if line.startswith("data: ")]
    assert data_lines[-1] == "[DONE]"
    assert "txn_test_001" in "".join(data_lines)
    assert "event: done" in text


def test_explain_unknown_transaction_is_404(client):
    assert client.get("/v1/explain/never-scored").status_code == 404


def test_openapi_documents_the_contract(client):
    spec = client.get("/openapi.json").json()
    assert "/v1/score" in spec["paths"]
    assert json.dumps(spec).count("merchant_category") >= 1
