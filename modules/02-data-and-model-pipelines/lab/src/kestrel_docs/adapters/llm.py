"""One interface, three providers. 📖 Lesson 1.4 (adapters) and the course conventions.

- `fake`   deterministic, offline: extracts the best sentence from the top source.
           It is NOT smart; it exists so tests and CI never need a model or a key.
- `ollama` local open-weight models (free): `ollama pull qwen2.5:1.5b-instruct`
- `openai` any OpenAI-compatible endpoint (OpenAI, vLLM, LM Studio, Groq, …)
"""

from __future__ import annotations

import re
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Literal, Protocol

import httpx

from kestrel_docs.config import Settings


@dataclass(frozen=True)
class Message:
    role: Literal["system", "user", "assistant"]
    content: str


@dataclass(frozen=True)
class Completion:
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float


class LLMClient(Protocol):
    async def complete(self, messages: list[Message], *, temperature: float = 0.0, max_tokens: int = 512) -> Completion: ...

    def stream(self, messages: list[Message], *, temperature: float = 0.0, max_tokens: int = 512) -> AsyncIterator[str]: ...


def approx_tokens(text: str) -> int:
    """~4 characters per token for English. Good enough for budgets; use the real tokenizer for billing."""
    return max(1, len(text) // 4)


_SOURCE_RE = re.compile(r"^\[(?P<doc>[a-z0-9-]+)\][^\n]*\n(?P<body>.*?)(?=^\[[a-z0-9-]+\]|\Z)", re.S | re.M)
_WORD_RE = re.compile(r"[a-z0-9€%+]+")
# Words that carry no meaning for matching (including the company name, which is everywhere).
_FAKE_STOPWORDS = frozenset(
    "a an the and or of to in on for with is are be can i my me do does how what when which who "
    "if it at by from as this that there you your we our will ever many much kestrel pay".split()
)


def _content_words(text: str) -> set[str]:
    words = set()
    for w in _WORD_RE.findall(text.lower()):
        if w in _FAKE_STOPWORDS:
            continue
        for suffix in ("ing", "ed", "s"):
            if len(w) > 4 and w.endswith(suffix) and not w.endswith("ss"):
                w = w[: -len(suffix)]
                break
        words.add(w)
    return words


class FakeLLM:
    """Extractive stand-in for an LLM: returns the source sentence that best overlaps the question.

    Deliberately simple and NOT smart. It refuses when no sentence covers at least 40%
    of the question's content words, and it skips sentences that are
    themselves questions (FAQ headings are not answers).
    """

    model = "fake-extractive-v1"
    min_overlap = 0.4

    def _answer(self, messages: list[Message]) -> str:
        prompt = messages[-1].content
        sources_part, _, question = prompt.rpartition("QUESTION:")
        q_words = _content_words(question)
        best, best_score, best_doc = "", 0.0, ""
        for rank, src in enumerate(_SOURCE_RE.finditer(sources_part)):
            body = re.sub(r"[*_`]+", "", src["body"])  # drop Markdown emphasis before reading sentences
            for sentence in re.split(r"(?<=[.!])\s+|\n+", body):
                sentence = sentence.strip()
                if sentence.endswith("?") or len(_content_words(sentence)) < 2 or set(sentence) <= set("|-: "):
                    continue
                overlap = len(q_words & _content_words(sentence)) / (len(q_words) or 1)
                score = overlap - 0.01 * rank  # earlier sources were ranked higher by retrieval
                if overlap >= self.min_overlap and score > best_score:
                    best, best_score, best_doc = sentence, score, src["doc"]
        if not best:
            return "I don't know based on the handbook."
        clean = best.strip(" -|#")
        clean = re.sub(r"\s*\|\s*", " | ", clean)
        return f"{clean} [{best_doc}]"

    async def complete(self, messages: list[Message], *, temperature: float = 0.0, max_tokens: int = 512) -> Completion:
        start = time.perf_counter()
        text = self._answer(messages)
        prompt_tokens = sum(approx_tokens(m.content) for m in messages)
        return Completion(text, self.model, prompt_tokens, approx_tokens(text), (time.perf_counter() - start) * 1000)

    async def stream(self, messages: list[Message], *, temperature: float = 0.0, max_tokens: int = 512) -> AsyncIterator[str]:
        for word in self._answer(messages).split(" "):
            yield word + " "


class OllamaLLM:
    def __init__(self, base_url: str, model: str, timeout_s: float):
        self.model = model
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout_s)

    async def complete(self, messages: list[Message], *, temperature: float = 0.0, max_tokens: int = 512) -> Completion:
        start = time.perf_counter()
        r = await self._client.post("/api/chat", json={
            "model": self.model,
            "messages": [m.__dict__ for m in messages],
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        })
        r.raise_for_status()
        data = r.json()
        return Completion(
            data["message"]["content"], self.model,
            data.get("prompt_eval_count", 0), data.get("eval_count", 0),
            (time.perf_counter() - start) * 1000,
        )

    async def stream(self, messages: list[Message], *, temperature: float = 0.0, max_tokens: int = 512) -> AsyncIterator[str]:
        completion = await self.complete(messages, temperature=temperature, max_tokens=max_tokens)
        yield completion.text  # Module 1 shows true token streaming; kept simple here.


class OpenAICompatibleLLM:
    def __init__(self, base_url: str, api_key: str, model: str, timeout_s: float):
        self.model = model
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout_s, headers={"Authorization": f"Bearer {api_key}"})

    async def complete(self, messages: list[Message], *, temperature: float = 0.0, max_tokens: int = 512) -> Completion:
        start = time.perf_counter()
        r = await self._client.post("/chat/completions", json={
            "model": self.model,
            "messages": [m.__dict__ for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        })
        r.raise_for_status()
        data = r.json()
        usage = data.get("usage", {})
        return Completion(
            data["choices"][0]["message"]["content"], self.model,
            usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0),
            (time.perf_counter() - start) * 1000,
        )

    async def stream(self, messages: list[Message], *, temperature: float = 0.0, max_tokens: int = 512) -> AsyncIterator[str]:
        completion = await self.complete(messages, temperature=temperature, max_tokens=max_tokens)
        yield completion.text


def build_llm(settings: Settings) -> LLMClient:
    if settings.llm_provider == "ollama":
        return OllamaLLM(settings.ollama_base_url, settings.ollama_model, settings.llm_timeout_s)
    if settings.llm_provider == "openai":
        return OpenAICompatibleLLM(settings.openai_base_url, settings.openai_api_key, settings.openai_model, settings.llm_timeout_s)
    return FakeLLM()
