"""The docs-assistant: retrieve → pack context → generate → cite.

This is the *system under test* for the Module 4 evals. It is intentionally
small, but it has every seam an eval and an on-call engineer care about:
retrieval results, the prompt version, token counts, refusals and a cache.
Each step emits an OpenTelemetry span (lesson 4.4).
"""

from __future__ import annotations

import re
import time
from collections import OrderedDict
from dataclasses import dataclass, field

from opentelemetry import trace

from kestrel_docs.adapters.llm import REFUSAL, LLMClient, Message
from kestrel_docs.domain.prompt_registry import PromptRegistry
from kestrel_docs.domain.retrieval import BM25Retriever, Retrieved

tracer = trace.get_tracer("kestrel_docs.assistant")

_CITATION_RE = re.compile(r"\[([a-z0-9][a-z0-9-]*)\]")


@dataclass
class Answer:
    text: str
    citations: list[str]
    refused: bool
    refusal_reason: str | None
    retrieved: list[Retrieved]
    prompt_version: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0
    cached: bool = False
    tool_calls: list[dict] = field(default_factory=list)

    @property
    def retrieved_doc_ids(self) -> list[str]:
        return [r.chunk.doc_id for r in self.retrieved]


def is_refusal(text: str) -> bool:
    lowered = text.lower()
    return "i don't know" in lowered or "i do not know" in lowered or "can't help with that" in lowered


def pack_context(retrieved: list[Retrieved]) -> str:
    """Wrap each chunk in a <doc> tag so the model (and the citations) can refer to it."""
    return "\n".join(f'<doc id="{r.chunk.doc_id}">\n{r.chunk.text}\n</doc>' for r in retrieved)


class DocsAssistant:
    def __init__(
        self,
        retriever: BM25Retriever,
        llm: LLMClient,
        registry: PromptRegistry,
        *,
        top_k: int = 3,
        history_turns: int = 2,
        cache_enabled: bool = True,
        cache_size: int = 512,
    ) -> None:
        self.retriever = retriever
        self.llm = llm
        self.registry = registry
        self.top_k = top_k
        self.history_turns = history_turns
        self.cache_enabled = cache_enabled
        self._cache: OrderedDict[tuple, Answer] = OrderedDict()
        self._cache_size = cache_size

    def _recent_user_turns(self, history: list[Message]) -> list[Message]:
        if self.history_turns <= 0:
            return []
        users = [m for m in history if m.role == "user"]
        return users[-self.history_turns :]

    async def ask(self, question: str, role: str, history: list[Message] | None = None) -> Answer:
        history = history or []
        prompt = self.registry.active()  # read every call: rollbacks apply without a restart
        recent = self._recent_user_turns(history)

        cache_key = (role, prompt.version, question.strip().lower(), tuple(m.content for m in recent))
        if self.cache_enabled and cache_key in self._cache:
            self._cache.move_to_end(cache_key)
            cached = self._cache[cache_key]
            return Answer(**{**cached.__dict__, "cached": True, "latency_ms": 0.0})

        start = time.perf_counter()
        with tracer.start_as_current_span("assistant.ask") as span:
            span.set_attribute("kestrel.role", role)
            span.set_attribute("kestrel.prompt.version", prompt.version)

            # 1) Retrieve. Follow-ups ("who decides on them?") need earlier turns.
            with tracer.start_as_current_span("retrieve") as rspan:
                query = " ".join([m.content for m in recent] + [question])
                retrieved = self.retriever.retrieve(query, role, k=self.top_k)
                rspan.set_attribute("retrieval.k", self.top_k)
                rspan.set_attribute("retrieval.doc_ids", [r.chunk.doc_id for r in retrieved])
                rspan.set_attribute("retrieval.top_score", retrieved[0].score if retrieved else 0.0)

            if not retrieved:
                # Nothing the user may see matches: refuse without paying for an LLM call.
                span.set_attribute("kestrel.refused", True)
                answer = Answer(
                    text=REFUSAL,
                    citations=[],
                    refused=True,
                    refusal_reason="no_context",
                    retrieved=[],
                    prompt_version=prompt.version,
                    model=self.llm.model,
                    latency_ms=(time.perf_counter() - start) * 1000,
                )
                self._remember(cache_key, answer)
                return answer

            # 2) Generate.
            messages = [Message("system", prompt.system)]
            if self.history_turns > 0:
                messages += history[-2 * self.history_turns :]
            # Escape angle brackets so a user cannot close our <doc> tags and forge
            # a fake "document" (tag spoofing, red-team case rt07, lesson 5.2).
            safe_question = question.replace("<", "&lt;").replace(">", "&gt;")
            messages.append(
                Message("user", prompt.render_user(context=pack_context(retrieved), question=safe_question))
            )
            with tracer.start_as_current_span("generate") as gspan:
                completion = await self.llm.complete(messages, temperature=0.0)
                # Attribute names follow the OpenTelemetry GenAI semantic conventions.
                gspan.set_attribute("gen_ai.request.model", completion.model)
                gspan.set_attribute("gen_ai.usage.input_tokens", completion.prompt_tokens)
                gspan.set_attribute("gen_ai.usage.output_tokens", completion.completion_tokens)

            refused = is_refusal(completion.text)
            span.set_attribute("kestrel.refused", refused)
            answer = Answer(
                text=completion.text,
                citations=sorted(set(_CITATION_RE.findall(completion.text))),
                refused=refused,
                refusal_reason="model" if refused else None,
                retrieved=retrieved,
                prompt_version=prompt.version,
                model=completion.model,
                prompt_tokens=completion.prompt_tokens,
                completion_tokens=completion.completion_tokens,
                latency_ms=(time.perf_counter() - start) * 1000,
            )
            self._remember(cache_key, answer)
            return answer

    def _remember(self, key: tuple, answer: Answer) -> None:
        if not self.cache_enabled:
            return
        self._cache[key] = answer
        if len(self._cache) > self._cache_size:
            self._cache.popitem(last=False)
