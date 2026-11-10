from fastapi.testclient import TestClient

from kestrel_foundations.hello_api import create_app
from kestrel_foundations.hello_client import call_echo

client = TestClient(create_app())


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_echo_repeats_and_propagates_request_id():
    r = client.post("/echo", json={"message": "hi", "repeat": 3}, headers={"X-Request-ID": "abc-123"})
    assert r.status_code == 200
    assert r.json() == {"echo": "hi hi hi", "length": 8, "request_id": "abc-123"}


def test_echo_generates_request_id_when_missing():
    assert len(client.post("/echo", json={"message": "hi"}).json()["request_id"]) == 36


def test_invalid_input_is_rejected_with_422():
    r = client.post("/echo", json={"message": "", "repeat": 9})
    assert r.status_code == 422
    fields = {err["loc"][-1] for err in r.json()["detail"]}
    assert fields == {"message", "repeat"}


def test_openapi_schema_is_generated():
    paths = client.get("/openapi.json").json()["paths"]
    assert "/echo" in paths and "/health" in paths


def test_client_helper_against_app():
    # TestClient is an httpx.Client, so the same helper works against the in-process app.
    assert call_echo(client, "yo", 2, request_id="t1") == {"echo": "yo yo", "length": 5, "request_id": "t1"}
