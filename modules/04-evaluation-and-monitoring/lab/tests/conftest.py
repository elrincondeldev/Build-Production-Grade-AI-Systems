import os
import shutil
from pathlib import Path

import pytest
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

# Tests must be hermetic: fake model, no network, no console span spam.
os.environ["KESTREL_LLM_PROVIDER"] = "fake"
os.environ["KESTREL_OTEL_EXPORTER"] = "none"

from kestrel_docs import observability  # noqa: E402

SPANS = InMemorySpanExporter()
observability.configure_tracing("none", span_exporter=SPANS)

LAB_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture
def spans() -> InMemorySpanExporter:
    SPANS.clear()
    return SPANS


@pytest.fixture
def registry_dir(tmp_path: Path) -> Path:
    """A private copy of the prompt registry so tests never touch the real pointer."""
    dst = tmp_path / "registry"
    shutil.copytree(LAB_DIR / "prompts" / "registry", dst)
    return dst
