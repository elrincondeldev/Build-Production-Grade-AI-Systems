import asyncio
import json

import httpx
import pytest

from kestrel_foundations.config import Settings
from kestrel_foundations.llm import (
    FakeLLM,
    Message,
    OllamaLLM,
    OpenAICompatibleLLM,
    estimate_cost_usd,
    estimate_tokens,
    get_llm,
)

MSGS = [Message("system", "Be brief."), Message("user", "What is a chargeback?")]


def run(coro):
    return asyncio.run(coro)


async def collect(aiter) -> str:
    return "".join([piece async for piece in aiter])


def test_fake_llm_is_deterministic():
    llm = FakeLLM()
    a, b = run(llm.complete(MSGS)), run(llm.complete(MSGS))
    assert a.text == b.text
    assert "What is a chargeback?" in a.text
    assert a.prompt_tokens > 0 and a.completion_tokens > 0


def test_fake_stream_matches_complete():
    llm = FakeLLM()
    assert run(collect(llm.stream(MSGS))) == run(llm.complete(MSGS)).text


def test_estimates():
    assert estimate_tokens("") == 0
    assert estimate_tokens("a" * 400) == 100
    # 1M input tokens at $1/M + 1M output tokens at $2/M = $3
    assert estimate_cost_usd(1_000_000, 1_000_000, 1.0, 2.0) == pytest.approx(3.0)


def test_factory_defaults_to_fake(monkeypatch):
    monkeypatch.delenv("KESTREL_LLM_PROVIDER", raising=False)
    assert isinstance(get_llm(Settings()), FakeLLM)


def test_factory_reads_env(monkeypatch):
    monkeypatch.setenv("KESTREL_LLM_PROVIDER", "ollama")
    monkeypatch.setenv("KESTREL_OLLAMA_MODEL", "tiny-model")
    llm = get_llm(Settings())
    assert isinstance(llm, OllamaLLM) and llm.model == "tiny-model"


def test_secret_is_not_leaked_in_repr(monkeypatch):
    monkeypatch.setenv("KESTREL_OPENAI_API_KEY", "sk-super-secret")
    s = Settings()
    assert "sk-super-secret" not in repr(s)
    assert s.openai_api_key.get_secret_value() == "sk-super-secret"


def test_ollama_adapter_against_fake_server():
    """httpx.MockTransport lets us test the adapter without a running Ollama."""

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert request.url.path == "/api/chat"
        assert body["stream"] is False
        assert body["options"]["temperature"] == 0.0
        return httpx.Response(
            200,
            json={"model": "qwen", "message": {"role": "assistant", "content": "A reversal."},
                  "prompt_eval_count": 12, "eval_count": 3},
        )

    llm = OllamaLLM("http://ollama.test", "qwen", transport=httpx.MockTransport(handler))
    c = run(llm.complete(MSGS))
    assert (c.text, c.prompt_tokens, c.completion_tokens) == ("A reversal.", 12, 3)


def test_ollama_streaming_parses_ndjson():
    lines = [
        {"message": {"content": "A "}, "done": False},
        {"message": {"content": "reversal."}, "done": False},
        {"done": True},
    ]
    body = "\n".join(json.dumps(x) for x in lines).encode()
    llm = OllamaLLM("http://ollama.test", "qwen", transport=httpx.MockTransport(lambda r: httpx.Response(200, content=body)))
    assert run(collect(llm.stream(MSGS))) == "A reversal."


def test_openai_adapter_sends_bearer_and_parses_usage():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer test-key"
        assert request.url.path == "/v1/chat/completions"
        return httpx.Response(
            200,
            json={"model": "m", "choices": [{"message": {"content": "Hi"}}],
                  "usage": {"prompt_tokens": 9, "completion_tokens": 1}},
        )

    llm = OpenAICompatibleLLM("http://api.test/v1", "test-key", "m", transport=httpx.MockTransport(handler))
    c = run(llm.complete(MSGS))
    assert (c.text, c.prompt_tokens, c.completion_tokens) == ("Hi", 9, 1)


def test_openai_streaming_parses_sse():
    events = [
        'data: {"choices":[{"delta":{"content":"Hel"}}]}',
        'data: {"choices":[{"delta":{"content":"lo"}}]}',
        "data: [DONE]",
    ]
    body = "\n\n".join(events).encode()
    llm = OpenAICompatibleLLM("http://api.test/v1", "k", "m", transport=httpx.MockTransport(lambda r: httpx.Response(200, content=body)))
    assert run(collect(llm.stream(MSGS))) == "Hello"


def test_http_errors_are_raised():
    llm = OllamaLLM("http://ollama.test", "qwen", transport=httpx.MockTransport(lambda r: httpx.Response(503)))
    with pytest.raises(httpx.HTTPStatusError):
        run(llm.complete(MSGS))
