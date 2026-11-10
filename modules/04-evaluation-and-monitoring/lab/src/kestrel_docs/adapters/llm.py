"""One interface, three LLM providers.

- ``FakeLLM``  (default) — deterministic, offline. Used by tests and CI.
- ``OllamaLLM`` — a local model served by Ollama.
- ``OpenAICompatibleLLM`` — any endpoint that speaks the OpenAI chat API.

Why a fake LLM in an *evaluation* lab?  Because an eval gate in CI must be
reproducible: same code + same data ⇒ same score. Real models are stochastic
and cost money. The fake is a tiny *extractive* simulator: it reads the
context the assistant packed into the prompt and copies the sentences that best
match the question. It also honours two prompt instructions ("cite …" and
"one sentence") so you can watch a prompt change cause a regression.
Switch to Ollama to see the same harness score a real model.
"""

from __future__ import annotations

import re
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol

import httpx

from kestrel_docs.config import Settings
from kestrel_docs.domain.text import content_tokens


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
    model: str

    async def complete(
        self, messages: list[Message], *, temperature: float = 0.0, max_tokens: int = 512
    ) -> Completion: ...

    def stream(
        self, messages: list[Message], *, temperature: float = 0.0, max_tokens: int = 512
    ) -> AsyncIterator[str]: ...


def approx_tokens(text: str) -> int:
    """Rough token count (~4 characters per token for English)."""
    return max(1, len(text) // 4)


REFUSAL = "I don't know based on the handbook."
_DOC_RE = re.compile(r'<doc id="(?P<id>[^"]+)">\n?(?P<text>.*?)</doc>', re.DOTALL)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")


class FakeLLM:
    """Deterministic extractive 'model'. See module docstring."""

    model = "fake-extractive-v1"

    def __init__(self, min_overlap: int = 2, max_sentences: int = 2) -> None:
        self.min_overlap = min_overlap
        self.max_sentences = max_sentences

    def _answer(self, messages: list[Message]) -> str:
        system = "\n".join(m.content for m in messages if m.role == "system").lower()
        user_turns = [m.content for m in messages if m.role == "user"]
        if not user_turns:
            return REFUSAL
        prompt = user_turns[-1]
        question = prompt.split("Question:")[-1]
        q_tokens = set(content_tokens(question))
        # Earlier user turns help with follow-ups like "Who decides on them?"
        for earlier in user_turns[:-1]:
            q_tokens |= set(content_tokens(earlier.split("Question:")[-1]))

        # (overlap, has_digit, chunk order, sentence, doc_id)
        candidates: list[tuple[int, int, int, str, str]] = []
        for order, match in enumerate(_DOC_RE.finditer(prompt)):
            doc_id = match.group("id")
            for raw in _SENTENCE_SPLIT.split(match.group("text")):
                if raw.lstrip().startswith("#") or raw.strip().endswith("?") or set(raw.strip()) <= set("|-: "):
                    continue  # headings, FAQ questions and table rulers are not answers
                sentence = re.sub(r"\*\*|`", "", raw).strip(" -*|")
                if len(sentence) < 12:
                    continue
                overlap = len(q_tokens & set(content_tokens(sentence)))
                # Tie-break: prefer sentences containing a number (facts, limits, prices).
                has_digit = int(any(ch.isdigit() for ch in sentence))
                candidates.append((overlap, has_digit, -order, sentence, doc_id))

        candidates.sort(key=lambda c: (c[0], c[1], c[2]), reverse=True)
        best = [c for c in candidates if c[0] >= self.min_overlap]
        if not best:
            return REFUSAL

        n = 1 if "one sentence" in system else self.max_sentences
        cite = "cite" in system
        parts = []
        for *_, sentence, doc_id in best[:n]:
            parts.append(f"{sentence} [{doc_id}]" if cite else sentence)
        return " ".join(parts)

    async def complete(
        self, messages: list[Message], *, temperature: float = 0.0, max_tokens: int = 512
    ) -> Completion:
        start = time.perf_counter()
        text = self._answer(messages)
        return Completion(
            text=text,
            model=self.model,
            prompt_tokens=sum(approx_tokens(m.content) for m in messages),
            completion_tokens=approx_tokens(text),
            latency_ms=(time.perf_counter() - start) * 1000,
        )

    async def stream(
        self, messages: list[Message], *, temperature: float = 0.0, max_tokens: int = 512
    ) -> AsyncIterator[str]:
        for word in self._answer(messages).split(" "):
            yield word + " "


class OllamaLLM:
    """Local model via Ollama's /api/chat endpoint (https://ollama.com)."""

    def __init__(self, base_url: str, model: str, timeout_s: float = 60.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_s = timeout_s

    async def complete(
        self, messages: list[Message], *, temperature: float = 0.0, max_tokens: int = 512
    ) -> Completion:
        payload = {
            "model": self.model,
            "messages": [m.__dict__ for m in messages],
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        start = time.perf_counter()
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            resp = await client.post(f"{self.base_url}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
        return Completion(
            text=data["message"]["content"].strip(),
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
    """Any OpenAI-compatible chat completions endpoint."""

    def __init__(self, base_url: str, api_key: str, model: str, timeout_s: float = 60.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_s = timeout_s

    async def complete(
        self, messages: list[Message], *, temperature: float = 0.0, max_tokens: int = 512
    ) -> Completion:
        payload = {
            "model": self.model,
            "messages": [m.__dict__ for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        start = time.perf_counter()
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            resp.raise_for_status()
            data = resp.json()
        usage = data.get("usage", {})
        return Completion(
            text=data["choices"][0]["message"]["content"].strip(),
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


def build_llm(settings: Settings) -> LLMClient:
    if settings.llm_provider == "ollama":
        return OllamaLLM(settings.ollama_base_url, settings.ollama_model, settings.llm_timeout_s)
    if settings.llm_provider == "openai":
        if settings.openai_api_key is None:
            raise ValueError("KESTREL_OPENAI_API_KEY is required when KESTREL_LLM_PROVIDER=openai")
        return OpenAICompatibleLLM(
            settings.openai_base_url,
            settings.openai_api_key.get_secret_value(),
            settings.openai_model,
            settings.llm_timeout_s,
        )
    return FakeLLM()
