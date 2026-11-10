"""One interface, three LLM providers (📖 lessons 1.3 and 1.4).

* ``fake``   deterministic, offline, instant. Tests and CI use this.
* ``ollama`` a local model through Ollama's HTTP API (free, private).
* ``openai`` any OpenAI-compatible endpoint (OpenAI, vLLM, LM Studio, Groq, …).

The rest of the code only sees ``LLMClient``. Swapping providers is a config change
(``KESTREL_LLM_PROVIDER``), which is the point of the adapter layer.

LLM calls are slow (hundreds of ms to tens of seconds) and almost entirely
*waiting on the network*, so they are ``async``: while one request waits for
tokens, the event loop serves other requests.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Literal, Protocol

import httpx

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


def _approx_tokens(text: str) -> int:
    # Rough rule of thumb for English: ~0.75 words per token. Good enough for a fake.
    return max(1, round(len(text.split()) / 0.75))


class FakeLLM:
    """Deterministic stand-in for a real model.

    It "answers" by restating the last user message in a fixed template, so
    tests can assert on exact output and run without network or GPU.
    ``token_delay_s`` simulates generation speed for streaming demos.
    """

    model = "fake-llm-v1"

    def __init__(self, token_delay_s: float = 0.0) -> None:
        self.token_delay_s = token_delay_s

    def _answer(self, messages: list[Message], max_tokens: int) -> str:
        last_user = next((m.content for m in reversed(messages) if m.role == "user"), "")
        words = f"[fake-llm] Summary of the request: {last_user}".split()
        return " ".join(words[:max_tokens])

    async def complete(
        self, messages: list[Message], *, temperature: float = 0.0, max_tokens: int = 512
    ) -> Completion:
        start = time.perf_counter()
        text = self._answer(messages, max_tokens)
        prompt = " ".join(m.content for m in messages)
        return Completion(
            text=text,
            model=self.model,
            prompt_tokens=_approx_tokens(prompt),
            completion_tokens=_approx_tokens(text),
            latency_ms=(time.perf_counter() - start) * 1000,
        )

    async def stream(
        self, messages: list[Message], *, temperature: float = 0.0, max_tokens: int = 512
    ) -> AsyncIterator[str]:
        words = self._answer(messages, max_tokens).split(" ")
        for i, word in enumerate(words):
            if self.token_delay_s:
                await asyncio.sleep(self.token_delay_s)
            yield word if i == 0 else " " + word


class OllamaLLM:
    """Local models via Ollama (https://ollama.com). Run ``ollama pull <model>`` first."""

    def __init__(self, base_url: str, model: str, timeout_s: float = 30.0) -> None:
        self.model = model
        self.client = httpx.AsyncClient(base_url=base_url, timeout=httpx.Timeout(timeout_s, connect=2.0))

    def _payload(self, messages: list[Message], temperature: float, max_tokens: int, stream: bool) -> dict:
        return {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": stream,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }

    async def complete(
        self, messages: list[Message], *, temperature: float = 0.0, max_tokens: int = 512
    ) -> Completion:
        start = time.perf_counter()
        resp = await self.client.post("/api/chat", json=self._payload(messages, temperature, max_tokens, False))
        resp.raise_for_status()
        data = resp.json()
        return Completion(
            text=data["message"]["content"],
            model=self.model,
            prompt_tokens=data.get("prompt_eval_count", 0),
            completion_tokens=data.get("eval_count", 0),
            latency_ms=(time.perf_counter() - start) * 1000,
        )

    async def stream(
        self, messages: list[Message], *, temperature: float = 0.0, max_tokens: int = 512
    ) -> AsyncIterator[str]:
        payload = self._payload(messages, temperature, max_tokens, True)
        async with self.client.stream("POST", "/api/chat", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():  # Ollama streams newline-delimited JSON
                if not line:
                    continue
                chunk = json.loads(line)
                if piece := chunk.get("message", {}).get("content"):
                    yield piece
                if chunk.get("done"):
                    break


class OpenAICompatibleLLM:
    """Any server implementing POST /chat/completions (OpenAI, vLLM, LM Studio…)."""

    def __init__(self, base_url: str, model: str, api_key: str | None, timeout_s: float = 30.0) -> None:
        self.model = model
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self.client = httpx.AsyncClient(
            base_url=base_url, headers=headers, timeout=httpx.Timeout(timeout_s, connect=2.0)
        )

    def _payload(self, messages: list[Message], temperature: float, max_tokens: int, stream: bool) -> dict:
        return {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }

    async def complete(
        self, messages: list[Message], *, temperature: float = 0.0, max_tokens: int = 512
    ) -> Completion:
        start = time.perf_counter()
        resp = await self.client.post(
            "/chat/completions", json=self._payload(messages, temperature, max_tokens, False)
        )
        resp.raise_for_status()
        data = resp.json()
        usage = data.get("usage", {})
        return Completion(
            text=data["choices"][0]["message"]["content"],
            model=data.get("model", self.model),
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            latency_ms=(time.perf_counter() - start) * 1000,
        )

    async def stream(
        self, messages: list[Message], *, temperature: float = 0.0, max_tokens: int = 512
    ) -> AsyncIterator[str]:
        payload = self._payload(messages, temperature, max_tokens, True)
        async with self.client.stream("POST", "/chat/completions", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():  # Server-Sent Events: "data: {...}"
                if not line.startswith("data: "):
                    continue
                data = line.removeprefix("data: ").strip()
                if data == "[DONE]":
                    break
                delta = json.loads(data)["choices"][0].get("delta", {})
                if piece := delta.get("content"):
                    yield piece


def build_llm(settings) -> LLMClient:  # settings: kestrel_fraud.config.Settings
    if settings.llm_provider == "ollama":
        return OllamaLLM(settings.ollama_base_url, settings.ollama_model, settings.llm_timeout_s)
    if settings.llm_provider == "openai":
        key = settings.openai_api_key.get_secret_value() if settings.openai_api_key else None
        return OpenAICompatibleLLM(settings.openai_base_url, settings.openai_model, key, settings.llm_timeout_s)
    return FakeLLM(token_delay_s=0.02 if settings.environment == "dev" else 0.0)
