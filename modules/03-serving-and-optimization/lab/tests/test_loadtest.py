import httpx

import loadtest
from kestrel_serving.adapters.llm import FakeLLM
from kestrel_serving.config import Settings
from kestrel_serving.main import create_app


def test_question_stream_repeat_rate():
    qs = loadtest.question_stream(["a", "b", "c"], n=200, repeat_rate=0.5, seed=0)
    assert len(qs) == 200
    repeats = len(qs) - len(set(qs))
    assert 70 < repeats < 130


async def test_run_load_in_process_and_report():
    app = create_app(Settings(cache_exact_enabled=True), llm=FakeLLM())
    questions = loadtest.question_stream(loadtest.load_questions(), 40, repeat_rate=0.5, seed=0)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as client:
        samples, wall = await loadtest.run_load(client, questions, concurrency=4)
    row = loadtest.report(samples, wall, "test", 4)
    assert row["requests"] == 40 and row["error_rate"] == "0.0%"
    assert row["p50_ms"] <= row["p95_ms"] <= row["p99_ms"]
    assert row["cache_hit_rate"] != "0%"
