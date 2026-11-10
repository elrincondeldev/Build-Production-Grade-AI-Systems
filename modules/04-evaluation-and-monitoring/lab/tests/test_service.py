from fastapi.testclient import TestClient

from kestrel_docs.config import Settings
from kestrel_docs.main import create_app


def client(registry_dir) -> TestClient:
    return TestClient(create_app(Settings(prompt_registry_dir=registry_dir, otel_exporter="none")))


def test_ask_returns_cited_answer(registry_dir):
    resp = client(registry_dir).post("/ask", json={"question": "What is the deadline to open a dispute after the transaction date?"})
    body = resp.json()
    assert resp.status_code == 200
    assert "120 days" in body["answer"]
    assert "card-dispute-process" in body["citations"]
    assert body["prompt_version"] == "v1"
    assert resp.headers["x-request-id"] == body["request_id"]


def test_customer_cannot_read_hr_documents(registry_dir):
    body = client(registry_dir).post(
        "/ask", json={"question": "What is the salary band for a Staff Engineer?", "role": "customer"}
    ).json()
    assert body["refused"] is True
    assert "salary-bands" not in body["citations"]


def test_metrics_endpoint_exposes_histograms_and_counters(registry_dir):
    c = client(registry_dir)
    r = c.post("/ask", json={"question": "What is the FX markup on the Plus plan?"})
    c.post("/feedback", json={"request_id": r.json()["request_id"], "rating": "down"})
    text = c.get("/metrics").text
    assert 'kestrel_request_latency_seconds_bucket{le="0.5",route="/ask"}' in text
    assert "kestrel_llm_tokens_total" in text
    assert 'kestrel_feedback_total{prompt_version="v1",rating="down"}' in text
    assert "kestrel_retrieval_top_score_bucket" in text


def test_second_identical_question_hits_cache(registry_dir):
    c = client(registry_dir)
    q = {"question": "What is my yearly learning budget?", "role": "employee"}
    assert c.post("/ask", json=q).json()["cached"] is False
    assert c.post("/ask", json=q).json()["cached"] is True


def test_trace_has_retrieve_and_generate_spans(registry_dir, spans):
    client(registry_dir).post("/ask", json={"question": "Are third-party ATM operator fees refundable?"})
    names = [s.name for s in spans.get_finished_spans()]
    assert {"assistant.ask", "retrieve", "generate"} <= set(names)
    generate = next(s for s in spans.get_finished_spans() if s.name == "generate")
    assert generate.attributes["gen_ai.usage.input_tokens"] > 0


def test_health_and_ready(registry_dir):
    c = client(registry_dir)
    assert c.get("/health").json() == {"status": "ok"}
    assert c.get("/ready").json()["chunks"] > 10
