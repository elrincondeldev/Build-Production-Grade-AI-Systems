"""The answer use case: cache -> retrieve -> prompt -> LLM -> cache. 📖 Lessons 3.4, 3.5."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from kestrel_serving.adapters.cache import ExactCache, SemanticCache
from kestrel_serving.adapters.llm import LLMClient, Message
from kestrel_serving.domain.retrieval import Chunk, Retriever

SYSTEM_PROMPT = (
    "You are Kestrel Pay's documentation assistant. Answer ONLY from the context. "
    "Cite the document id in square brackets. If the context does not contain the answer, "
    "say you don't know."
)


def build_prompt(question: str, chunks: list[Chunk]) -> list[Message]:
    context = "\n\n".join(f"[{c.doc_id}] {c.text}" for c in chunks)
    return [
        Message("system", SYSTEM_PROMPT),
        Message("user", f"Context:\n{context}\n\nQuestion: {question}"),
    ]


@dataclass
class Answer:
    answer: str
    citations: list[str]
    model: str
    cache: str | None = None  # None | "exact" | "semantic"
    timings_ms: dict[str, float] = field(default_factory=dict)
    prompt_tokens: int = 0
    completion_tokens: int = 0


class AnswerService:
    def __init__(
        self,
        retriever: Retriever,
        llm: LLMClient,
        exact_cache: ExactCache | None,
        semantic_cache: SemanticCache | None,
        top_k: int = 3,
        cache_scope: str = "v1",
    ) -> None:
        self.retriever = retriever
        self.llm = llm
        self.exact_cache = exact_cache
        self.semantic_cache = semantic_cache
        self.top_k = top_k
        # Everything that changes the answer belongs in the cache scope (prompt version, model, ...).
        self.cache_scope = cache_scope

    def _lookup(self, question: str) -> Answer | None:
        if self.exact_cache is not None:
            hit = self.exact_cache.get(question, self.cache_scope)
            if hit is not None:
                return Answer(**{**hit.__dict__, "cache": "exact", "timings_ms": {}})
        if self.semantic_cache is not None:
            sem = self.semantic_cache.get(question, self.cache_scope)
            if sem is not None:
                return Answer(**{**sem.value.__dict__, "cache": "semantic", "timings_ms": {}})
        return None

    def _store(self, question: str, answer: Answer) -> None:
        if self.exact_cache is not None:
            self.exact_cache.put(question, answer, self.cache_scope)
        if self.semantic_cache is not None:
            self.semantic_cache.put(question, answer, self.cache_scope)

    async def answer(self, question: str) -> Answer:
        t0 = time.perf_counter()
        cached = self._lookup(question)
        t1 = time.perf_counter()
        if cached is not None:
            cached.timings_ms = {"cache_ms": round((t1 - t0) * 1000, 2)}
            return cached
        chunks = self.retriever.search(question, self.top_k)
        t2 = time.perf_counter()
        completion = await self.llm.complete(build_prompt(question, chunks))
        t3 = time.perf_counter()
        result = Answer(
            answer=completion.text,
            citations=sorted({c.doc_id for c in chunks}),
            model=completion.model,
            prompt_tokens=completion.prompt_tokens,
            completion_tokens=completion.completion_tokens,
            timings_ms={
                "cache_ms": round((t1 - t0) * 1000, 2),
                "retrieval_ms": round((t2 - t1) * 1000, 2),
                "llm_ms": round((t3 - t2) * 1000, 2),
            },
        )
        self._store(question, result)
        return result

    async def stream(self, question: str) -> AsyncIterator[str]:
        """Streaming path: same cache semantics, tokens yielded as they are produced."""
        cached = self._lookup(question)
        if cached is not None:
            yield cached.answer
            return
        chunks = self.retriever.search(question, self.top_k)
        pieces: list[str] = []
        async for piece in self.llm.stream(build_prompt(question, chunks)):
            pieces.append(piece)
            yield piece
        self._store(
            question,
            Answer(answer="".join(pieces), citations=sorted({c.doc_id for c in chunks}), model="stream"),
        )
