from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kestrel_docs_assistant.adapters.llm import Completion, FakeLLM, Message
from kestrel_docs_assistant.adapters.tokens import Principal, issue_token
from kestrel_docs_assistant.config import LAB_DIR, Settings
from kestrel_docs_assistant.domain.assistant import DocsAssistant, Layers
from kestrel_docs_assistant.domain.documents import chunk_document, load_corpus
from kestrel_docs_assistant.domain.guardrails import HeuristicInjectionDetector
from kestrel_docs_assistant.domain.registry import PolicyRegistry
from kestrel_docs_assistant.domain.retrieval import PermissionAwareBM25
from kestrel_docs_assistant.main import create_app

SECRET = "test-secret-0123456789abcdef0123456789"


class RecordingLLM:
    """Wraps a model and records every prompt it receives, so tests can prove
    what did (and did not) reach the model."""

    def __init__(self, inner: FakeLLM) -> None:
        self.inner = inner
        self.prompts: list[str] = []

    async def complete(self, messages: list[Message], **kw: object) -> Completion:
        self.prompts.append("\n".join(m.content for m in messages))
        return await self.inner.complete(messages, **kw)  # type: ignore[arg-type]

    def stream(self, messages, **kw):  # noqa: ANN001, ANN201
        return self.inner.stream(messages, **kw)


@pytest.fixture
def registry_dir(tmp_path: Path) -> Path:
    dst = tmp_path / "registry"
    shutil.copytree(LAB_DIR / "registry", dst)
    return dst


@pytest.fixture
def settings(tmp_path: Path, registry_dir: Path) -> Settings:
    return Settings(env="test", jwt_secret=SECRET, registry_dir=registry_dir, audit_log_path=tmp_path / "audit.jsonl")


@pytest.fixture
def bundle(registry_dir: Path):
    return PolicyRegistry(registry_dir).active_bundle()


def build_assistant(
    settings: Settings,
    bundle,
    *,
    sanitize: bool = True,
    layers: Layers = Layers(),
    mode: str = "gullible",
) -> tuple[DocsAssistant, RecordingLLM]:
    chunks = [c for d in load_corpus(settings.handbook_dir, sanitize_content=sanitize) for c in chunk_document(d)]
    llm = RecordingLLM(FakeLLM(mode=mode))  # type: ignore[arg-type]
    assistant = DocsAssistant(
        index=PermissionAwareBM25(chunks), llm=llm, bundle=bundle, detector=HeuristicInjectionDetector(), layers=layers
    )
    return assistant, llm


async def ask(assistant: DocsAssistant, question: str, role: str):
    return await assistant.answer(question, Principal(f"test-{role}", role), str(uuid.uuid4()))


@pytest.fixture
def client(settings: Settings):
    with TestClient(create_app(settings)) as c:
        yield c


@pytest.fixture
def token(settings: Settings):
    def _make(role: str = "customer", sub: str = "alice") -> str:
        return issue_token(sub, role, settings.jwt_secret, issuer=settings.jwt_issuer, audience=settings.jwt_audience)

    return _make
