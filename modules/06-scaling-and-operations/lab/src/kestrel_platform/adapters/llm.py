"""One LLM interface, three providers (course convention).

- fake:   deterministic, offline. Used by tests and CI.
- ollama: local models through http://localhost:11434
- openai: any OpenAI-compatible endpoint (OpenAI, vLLM, LM Studio, ...)

Select with KESTREL_LLM_PROVIDER.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol

import httpx

from kestrel_platform.config import Settings, get_settings


@dataclass(frozen=True)
class Message:
    role: str  # system | user | assistant
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
    # ~4 characters per token for English text; good enough for budgets in tests.
    return max(1, len(text) // 4)


class FakeLLM:
    """Deterministic stand-in. It answers with a fixed sentence, which is *not* valid
    planner JSON, so the LLM planner exercises its fallback path in tests."""

    model = "fake-llm"

    def __init__(self, reply: str | None = None) -> None:
        self.reply = reply or "I am a fake model and cannot produce a plan."

    async def complete(
        self, messages: list[Message], *, temperature: float = 0.0, max_tokens: int = 512
    ) -> Completion:
        prompt = "\n".join(m.content for m in messages)
        return Completion(self.reply, self.model, _approx_tokens(prompt), _approx_tokens(self.reply), 0.0)

    async def stream(
        self, messages: list[Message], *, temperature: float = 0.0, max_tokens: int = 512
    ) -> AsyncIterator[str]:
        for word in self.reply.split(" "):
            yield word + " "


class OllamaLLM:
    def __init__(self, base_url: str, model: str, timeout_s: float = 60.0) -> None:
        self.base_url, self.model, self.timeout_s = base_url.rstrip("/"), model, timeout_s

    async def complete(
        self, messages: list[Message], *, temperature: float = 0.0, max_tokens: int = 512
    ) -> Completion:
        start = time.perf_counter()
        payload = {
            "model": self.model,
            "messages": [m.__dict__ for m in messages],
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            r = await client.post(f"{self.base_url}/api/chat", json=payload)
            r.raise_for_status()
            data = r.json()
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
        completion = await self.complete(messages, temperature=temperature, max_tokens=max_tokens)
        yield completion.text


class OpenAICompatibleLLM:
    def __init__(self, base_url: str, api_key: str | None, model: str, timeout_s: float = 60.0) -> None:
        self.base_url, self.api_key, self.model, self.timeout_s = base_url.rstrip("/"), api_key, model, timeout_s

    async def complete(
        self, messages: list[Message], *, temperature: float = 0.0, max_tokens: int = 512
    ) -> Completion:
        start = time.perf_counter()
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        payload = {
            "model": self.model,
            "messages": [m.__dict__ for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            r = await client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
        usage = data.get("usage", {})
        return Completion(
            text=data["choices"][0]["message"]["content"],
            model=self.model,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            latency_ms=(time.perf_counter() - start) * 1000,
        )

    async def stream(
        self, messages: list[Message], *, temperature: float = 0.0, max_tokens: int = 512
    ) -> AsyncIterator[str]:
        completion = await self.complete(messages, temperature=temperature, max_tokens=max_tokens)
        yield completion.text


def build_llm(settings: Settings | None = None) -> LLMClient:
    s = settings or get_settings()
    if s.llm_provider == "fake":
        return FakeLLM()
    if s.llm_provider == "ollama":
        return OllamaLLM(s.ollama_base_url, s.ollama_model)
    if s.llm_provider == "openai":
        return OpenAICompatibleLLM(s.openai_base_url, s.openai_api_key, s.openai_model)
    raise ValueError(f"Unknown KESTREL_LLM_PROVIDER={s.llm_provider!r}")
