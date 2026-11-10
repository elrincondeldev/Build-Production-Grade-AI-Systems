"""One interface, three providers. Swap models without touching business logic.

* ``fake``   deterministic, offline, with *simulated* latency that follows the real
             cost structure (prefill per prompt token + decode per output token).
* ``ollama`` a local model through Ollama's HTTP API.
* ``openai`` any OpenAI-compatible server: OpenAI itself, or a vLLM / SGLang / TGI /
             llama.cpp server you run yourself. 📖 Lesson 3.1.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol

import httpx

from kestrel_serving.config import Settings


@dataclass(frozen=True)
class Message:
    role: str  # "system" | "user" | "assistant"
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


def approx_tokens(text: str) -> int:
    """~4 characters per token for English text. Good enough for budgeting, not for billing."""
    return max(1, len(text) // 4)


class FakeLLM:
    """Answers by quoting the first sentence of the first context block.

    Latency = prefill_ms_per_token * prompt_tokens + decode_ms_per_token * output_tokens,
    so caching and load tests behave like a real (slow) model would.
    """

    model = "fake-llm"

    def __init__(
        self, prefill_ms_per_token: float = 0.0, decode_ms_per_token: float = 0.0, max_concurrency: int = 0
    ) -> None:
        self.prefill_ms_per_token = prefill_ms_per_token
        self.decode_ms_per_token = decode_ms_per_token
        self.calls = 0  # handy in tests: proves a cache hit never reached the model
        # A real model server has finite capacity. With max_concurrency > 0, extra requests
        # wait in line, so load tests show queueing and saturation (📖 lesson 3.4).
        self._slots = asyncio.Semaphore(max_concurrency) if max_concurrency > 0 else None

    async def _sleep(self, ms: float) -> None:
        if self._slots is None:
            await asyncio.sleep(ms / 1000)
            return
        async with self._slots:
            await asyncio.sleep(ms / 1000)

    @staticmethod
    def _answer(messages: list[Message]) -> str:
        prompt = messages[-1].content
        match = re.search(r"\[(?P<doc>[\w-]+)\]\s*(?P<text>.+?)(?:\n\n|\Z)", prompt, re.S)
        if not match:
            return "I don't know based on the provided documents."
        sentence = re.split(r"(?<=[.!?])\s", match["text"].strip().replace("\n", " "))[0]
        return f"{sentence} [{match['doc']}]"

    async def complete(
        self, messages: list[Message], *, temperature: float = 0.0, max_tokens: int = 512
    ) -> Completion:
        start = time.perf_counter()
        self.calls += 1
        text = self._answer(messages)
        prompt_tokens = sum(approx_tokens(m.content) for m in messages)
        completion_tokens = min(approx_tokens(text), max_tokens)
        delay_ms = self.prefill_ms_per_token * prompt_tokens + self.decode_ms_per_token * completion_tokens
        await self._sleep(delay_ms)
        return Completion(text, self.model, prompt_tokens, completion_tokens, (time.perf_counter() - start) * 1000)

    async def stream(
        self, messages: list[Message], *, temperature: float = 0.0, max_tokens: int = 512
    ) -> AsyncIterator[str]:
        self.calls += 1
        text = self._answer(messages)
        prompt_tokens = sum(approx_tokens(m.content) for m in messages)
        words = text.split(" ")
        if self._slots is not None:
            await self._slots.acquire()  # hold one "GPU slot" for the whole generation
        try:
            await asyncio.sleep(self.prefill_ms_per_token * prompt_tokens / 1000)  # time to first token
            for i, word in enumerate(words):
                await asyncio.sleep(self.decode_ms_per_token * approx_tokens(word + " ") / 1000)
                yield word if i == 0 else " " + word
        finally:
            if self._slots is not None:
                self._slots.release()


class OllamaLLM:
    def __init__(self, base_url: str, model: str, timeout_s: float) -> None:
        self.model = model
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout_s)

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
        resp = await self._client.post("/api/chat", json=self._payload(messages, temperature, max_tokens, False))
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
        async with self._client.stream("POST", "/api/chat", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line:
                    chunk = json.loads(line)
                    if text := chunk.get("message", {}).get("content"):
                        yield text


class OpenAICompatibleLLM:
    def __init__(self, base_url: str, api_key: str, model: str, timeout_s: float) -> None:
        self.model = model
        self._client = httpx.AsyncClient(
            base_url=base_url, timeout=timeout_s, headers={"Authorization": f"Bearer {api_key}"}
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
        resp = await self._client.post("/chat/completions", json=self._payload(messages, temperature, max_tokens, False))
        resp.raise_for_status()
        data = resp.json()
        usage = data.get("usage") or {}
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
        async with self._client.stream("POST", "/chat/completions", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():  # Server-Sent Events: "data: {...}"
                if not line.startswith("data: ") or line == "data: [DONE]":
                    continue
                delta = json.loads(line[6:])["choices"][0].get("delta", {})
                if text := delta.get("content"):
                    yield text


def build_llm(settings: Settings) -> LLMClient:
    if settings.llm_provider == "ollama":
        return OllamaLLM(settings.ollama_url, settings.ollama_model, settings.llm_timeout_s)
    if settings.llm_provider == "openai":
        return OpenAICompatibleLLM(
            settings.openai_base_url, settings.openai_api_key, settings.openai_model, settings.llm_timeout_s
        )
    return FakeLLM(settings.fake_prefill_ms_per_token, settings.fake_decode_ms_per_token, settings.fake_max_concurrency)
