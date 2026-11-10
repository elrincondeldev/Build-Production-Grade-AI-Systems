"""One interface, three LLM providers.

📖 See lesson 0.5 "LLMs in one hour".

Why an interface? Your application code should not care whether the answer
comes from a fake model (tests), a local model (Ollama) or a paid API. Swapping
providers becomes a config change, not a rewrite. Every later module uses this
same shape.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Literal, Protocol

import httpx

from .config import Settings

Role = Literal["system", "user", "assistant"]


@dataclass(frozen=True)
class Message:
    role: Role
    content: str


@dataclass(frozen=True)
class Completion:
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float


class LLMClient(Protocol):
    async def complete(
        self, messages: list[Message], *, temperature: float = 0.0, max_tokens: int = 512
    ) -> Completion: ...

    def stream(
        self, messages: list[Message], *, temperature: float = 0.0, max_tokens: int = 512
    ) -> AsyncIterator[str]: ...


def estimate_tokens(text: str) -> int:
    """Rough rule of thumb for English: ~4 characters per token.

    Real tokenizers differ per model; use this only for estimates, never billing.
    """
    return max(1, round(len(text) / 4)) if text else 0


def estimate_cost_usd(
    prompt_tokens: int, completion_tokens: int, input_price_per_m: float, output_price_per_m: float
) -> float:
    """Cost = tokens / 1,000,000 × price per million tokens (input and output priced separately)."""
    return prompt_tokens / 1e6 * input_price_per_m + completion_tokens / 1e6 * output_price_per_m


def _messages_payload(messages: list[Message]) -> list[dict[str, str]]:
    return [{"role": m.role, "content": m.content} for m in messages]


class FakeLLM:
    """Deterministic stand-in for a real model: same input -> same output, no network.

    Tests and CI use it so they are fast, free and never flaky. It does NOT
    understand anything; it only proves that the plumbing around the model works.
    """

    model = "fake-llm-v1"

    def _answer(self, messages: list[Message]) -> str:
        last_user = next((m.content for m in reversed(messages) if m.role == "user"), "")
        digest = hashlib.sha256(last_user.encode()).hexdigest()[:8]
        preview = last_user if len(last_user) <= 80 else last_user[:77] + "..."
        return (
            f'[fake-llm:{digest}] You asked: "{preview}". '
            "A real model would answer here. Set KESTREL_LLM_PROVIDER=ollama to use a local model."
        )

    async def complete(
        self, messages: list[Message], *, temperature: float = 0.0, max_tokens: int = 512
    ) -> Completion:
        start = time.perf_counter()
        text = self._answer(messages)
        prompt = " ".join(m.content for m in messages)
        return Completion(
            text=text,
            model=self.model,
            prompt_tokens=estimate_tokens(prompt),
            completion_tokens=estimate_tokens(text),
            latency_ms=(time.perf_counter() - start) * 1000,
        )

    async def stream(
        self, messages: list[Message], *, temperature: float = 0.0, max_tokens: int = 512
    ) -> AsyncIterator[str]:
        words = self._answer(messages).split(" ")
        for i, word in enumerate(words):
            yield word if i == 0 else " " + word


class OllamaLLM:
    """Local models via Ollama's HTTP API (https://github.com/ollama/ollama/blob/main/docs/api.md)."""

    def __init__(self, base_url: str, model: str, timeout_s: float = 60.0, transport: httpx.AsyncBaseTransport | None = None):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_s = timeout_s
        self._transport = transport  # injectable so tests can fake the server

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout_s, transport=self._transport)

    def _payload(self, messages: list[Message], temperature: float, max_tokens: int, stream: bool) -> dict:
        return {
            "model": self.model,
            "messages": _messages_payload(messages),
            "stream": stream,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }

    async def complete(
        self, messages: list[Message], *, temperature: float = 0.0, max_tokens: int = 512
    ) -> Completion:
        start = time.perf_counter()
        async with self._client() as client:
            resp = await client.post("/api/chat", json=self._payload(messages, temperature, max_tokens, False))
            resp.raise_for_status()
            data = resp.json()
        text = data["message"]["content"]
        return Completion(
            text=text,
            model=data.get("model", self.model),
            prompt_tokens=int(data.get("prompt_eval_count", 0)),
            completion_tokens=int(data.get("eval_count", estimate_tokens(text))),
            latency_ms=(time.perf_counter() - start) * 1000,
        )

    async def stream(
        self, messages: list[Message], *, temperature: float = 0.0, max_tokens: int = 512
    ) -> AsyncIterator[str]:
        async with self._client() as client:
            payload = self._payload(messages, temperature, max_tokens, True)
            async with client.stream("POST", "/api/chat", json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():  # Ollama streams one JSON object per line
                    if not line.strip():
                        continue
                    chunk = json.loads(line)
                    if chunk.get("done"):
                        break
                    yield chunk.get("message", {}).get("content", "")


class OpenAICompatibleLLM:
    """Any server that speaks the OpenAI Chat Completions API (OpenAI, vLLM, LM Studio, many hosts)."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout_s: float = 60.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_s = timeout_s
        self._headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._transport = transport

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.base_url, headers=self._headers, timeout=self.timeout_s, transport=self._transport
        )

    def _payload(self, messages: list[Message], temperature: float, max_tokens: int, stream: bool) -> dict:
        return {
            "model": self.model,
            "messages": _messages_payload(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }

    async def complete(
        self, messages: list[Message], *, temperature: float = 0.0, max_tokens: int = 512
    ) -> Completion:
        start = time.perf_counter()
        async with self._client() as client:
            resp = await client.post("/chat/completions", json=self._payload(messages, temperature, max_tokens, False))
            resp.raise_for_status()
            data = resp.json()
        usage = data.get("usage") or {}
        text = data["choices"][0]["message"]["content"]
        return Completion(
            text=text,
            model=data.get("model", self.model),
            prompt_tokens=int(usage.get("prompt_tokens", 0)),
            completion_tokens=int(usage.get("completion_tokens", estimate_tokens(text))),
            latency_ms=(time.perf_counter() - start) * 1000,
        )

    async def stream(
        self, messages: list[Message], *, temperature: float = 0.0, max_tokens: int = 512
    ) -> AsyncIterator[str]:
        async with self._client() as client:
            payload = self._payload(messages, temperature, max_tokens, True)
            async with client.stream("POST", "/chat/completions", json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():  # Server-Sent Events: "data: {...}"
                    if not line.startswith("data:"):
                        continue
                    data = line.removeprefix("data:").strip()
                    if data == "[DONE]":
                        break
                    delta = json.loads(data)["choices"][0].get("delta", {})
                    if delta.get("content"):
                        yield delta["content"]


def get_llm(settings: Settings | None = None) -> LLMClient:
    """Factory: pick the provider from configuration."""
    s = settings or Settings()
    if s.llm_provider == "fake":
        return FakeLLM()
    if s.llm_provider == "ollama":
        return OllamaLLM(s.ollama_base_url, s.ollama_model, s.llm_timeout_s)
    if s.llm_provider == "openai":
        return OpenAICompatibleLLM(
            s.openai_base_url, s.openai_api_key.get_secret_value(), s.openai_model, s.llm_timeout_s
        )
    raise ValueError(f"Unknown LLM provider: {s.llm_provider}")
