"""Ask the assistant from the command line, no server or token needed.

    uv run python scripts/ask.py --role customer "How long do I have to open a card dispute?"
    uv run python scripts/ask.py --role customer --show-prompt "Are refunds unlimited and instant?"

Respects the same KESTREL_* settings as the API, so the "Break it" experiments
work here too, e.g.  KESTREL_SANITIZE_INGEST=false uv run python scripts/ask.py ...
"""

from __future__ import annotations

import argparse
import asyncio
import uuid

from kestrel_docs_assistant.adapters.llm import Completion, LLMClient, Message, build_llm
from kestrel_docs_assistant.adapters.tokens import Principal
from kestrel_docs_assistant.config import get_settings
from kestrel_docs_assistant.domain.access import ROLE_ACCESS
from kestrel_docs_assistant.domain.assistant import DocsAssistant, Layers
from kestrel_docs_assistant.domain.documents import chunk_document, load_corpus
from kestrel_docs_assistant.domain.guardrails import HeuristicInjectionDetector
from kestrel_docs_assistant.domain.registry import PolicyRegistry
from kestrel_docs_assistant.domain.retrieval import PermissionAwareBM25


class PrintingLLM:
    def __init__(self, inner: LLMClient) -> None:
        self.inner = inner

    async def complete(self, messages: list[Message], **kw: object) -> Completion:
        for m in messages:
            print(f"----- {m.role.upper()} -----\n{m.content}\n")
        completion = await self.inner.complete(messages, **kw)  # type: ignore[arg-type]
        print(f"----- RAW MODEL OUTPUT -----\n{completion.text}\n")
        return completion

    def stream(self, messages, **kw):  # noqa: ANN001, ANN201
        return self.inner.stream(messages, **kw)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("question")
    parser.add_argument("--role", default="customer", choices=sorted(ROLE_ACCESS))
    parser.add_argument("--show-prompt", action="store_true")
    args = parser.parse_args()

    s = get_settings()
    chunks = [c for d in load_corpus(s.handbook_dir, sanitize_content=s.sanitize_ingest) for c in chunk_document(d)]
    llm = build_llm(s)
    assistant = DocsAssistant(
        index=PermissionAwareBM25(chunks),
        llm=PrintingLLM(llm) if args.show_prompt else llm,
        bundle=PolicyRegistry(s.registry_dir).active_bundle(),
        detector=HeuristicInjectionDetector(),
        layers=Layers(s.input_guardrails, s.scan_retrieved_chunks, s.output_guardrails),
    )
    result = asyncio.run(assistant.answer(args.question, Principal("cli", args.role), str(uuid.uuid4())))
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
