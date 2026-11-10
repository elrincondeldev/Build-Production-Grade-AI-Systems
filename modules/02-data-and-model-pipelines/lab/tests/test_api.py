import pytest
from fastapi.testclient import TestClient

from kestrel_docs.main import create_app


@pytest.fixture(scope="module")
def client(settings):
    with TestClient(create_app(settings)) as c:  # `with` runs the startup lifespan (index build)
        yield c


def test_health_and_readiness(client):
    assert client.get("/healthz").json() == {"status": "ok"}
    ready = client.get("/readyz").json()
    assert ready["documents"] == 14 and ready["chunks"] > 14


def test_answer_has_valid_citations(client):
    r = client.post("/v1/ask", json={"question": "How many days do I have to request a refund for a fee?"})
    assert r.status_code == 200
    body = r.json()
    assert "60 days" in body["answer"]
    cited = {c["doc_id"] for c in body["citations"]}
    assert cited == {"refund-policy"}
    assert cited <= {ch["doc_id"] for ch in body["chunks"]}  # every citation points at a provided chunk


def test_customer_cannot_retrieve_hr_documents(client):
    body = client.post("/v1/ask", json={"question": "What is the salary band for a Staff Engineer?", "role": "customer"}).json()
    assert all(ch["access"] == "public" for ch in body["chunks"])
    assert "€72,000" not in body["answer"]


def test_hr_can_retrieve_salary_bands(client):
    body = client.post("/v1/ask", json={"question": "What is the salary band for a Senior Engineer?", "role": "hr"}).json()
    assert "salary-bands" in {c["doc_id"] for c in body["citations"]}


def test_request_validation(client):
    assert client.post("/v1/ask", json={"question": "hi"}).status_code == 422
    assert client.post("/v1/ask", json={"question": "valid question", "role": "admin"}).status_code == 422
