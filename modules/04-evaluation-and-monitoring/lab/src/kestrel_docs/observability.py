"""Metrics (Prometheus) and traces (OpenTelemetry). 📖 See lesson 4.4.

Two complementary signals:

- **Metrics** are cheap numbers aggregated over time: "p95 latency over 5 min",
  "refusal rate". Great for dashboards and alerts.
- **Traces** are the story of *one* request: which chunks were retrieved,
  which prompt version, how many tokens. Great for debugging a bad answer.

Metric names follow Prometheus conventions: ``<namespace>_<what>_<unit>`` and
``_total`` for counters.
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

# ----------------------------------------------------------------- metrics
REQUEST_LATENCY = Histogram(
    "kestrel_request_latency_seconds",
    "End-to-end HTTP request latency.",
    ["route"],
    # Buckets should bracket your SLO (e.g. p95 < 2 s) with resolution on both sides.
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0),
)
REQUESTS = Counter("kestrel_requests_total", "HTTP requests.", ["route", "status"])
LLM_TOKENS = Counter("kestrel_llm_tokens_total", "LLM tokens used.", ["type", "model"])
CACHE_LOOKUPS = Counter("kestrel_cache_lookups_total", "Answer cache lookups.", ["result"])
REFUSALS = Counter("kestrel_refusals_total", "Answers that refused.", ["reason"])
ANSWERS = Counter("kestrel_answers_total", "Answers served.", ["prompt_version"])
FEEDBACK = Counter(
    "kestrel_feedback_total", "User thumbs up/down: the outcome signal.", ["rating", "prompt_version"]
)
RETRIEVAL_TOP_SCORE = Histogram(
    "kestrel_retrieval_top_score",
    "BM25 score of the best retrieved chunk. A drop means users ask about things the docs don't cover.",
    buckets=(0.0, 1.0, 2.0, 4.0, 6.0, 8.0, 10.0, 15.0, 20.0),
)
PROMPT_INFO = Gauge("kestrel_prompt_version_info", "Active prompt version (value is always 1).", ["name", "version"])


# ------------------------------------------------------------------ traces
_tracing_configured = False


def configure_tracing(exporter: str = "console", *, otlp_endpoint: str | None = None, span_exporter=None) -> None:  # noqa: ANN001
    """Install a global TracerProvider once per process.

    exporter: "console" prints spans as JSON to stdout (good for learning),
    "otlp" ships them to a collector (Jaeger, Tempo, …), "none" disables export.
    ``span_exporter`` lets tests pass an in-memory exporter.
    """
    global _tracing_configured
    if _tracing_configured:
        return

    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter, SimpleSpanProcessor

    provider = TracerProvider(resource=Resource.create({"service.name": "docs-assistant"}))
    if span_exporter is not None:
        provider.add_span_processor(SimpleSpanProcessor(span_exporter))
    elif exporter == "console":
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    elif exporter == "otlp":
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter  # optional extra

        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint)))
    trace.set_tracer_provider(provider)
    _tracing_configured = True
