from kestrel_serving.sim import CostModel, Request, generate_workload, simulate


def test_single_request_cost_is_prefill_plus_decode():
    cost = CostModel(prefill_ms_per_token=0.1, decode_base_ms=20, decode_ms_per_seq=1)
    report = simulate("none", [Request(0, 0.0, prompt_tokens=1000, output_tokens=10)], cost)
    r = report.results[0]
    assert r.ttft_ms == 100 + 21  # prefill + first decode step
    assert r.latency_ms == 100 + 10 * 21


def test_workload_is_deterministic():
    assert generate_workload(50, 2.0, seed=3) == generate_workload(50, 2.0, seed=3)


def test_continuous_batching_wins_under_load():
    workload = generate_workload(300, requests_per_s=3.0, seed=7, output_tokens_median=80)
    none = simulate("none", workload)
    dynamic = simulate("dynamic", workload, max_batch=32, max_wait_ms=100)
    continuous = simulate("continuous", workload, max_batch=32)

    assert continuous.throughput_tokens_per_s >= dynamic.throughput_tokens_per_s >= none.throughput_tokens_per_s
    assert continuous.latency(95) < dynamic.latency(95) < none.latency(95)
    # Iteration-level scheduling lets new requests start almost immediately.
    assert continuous.ttft(50) < dynamic.ttft(50)


def test_all_policies_complete_every_request():
    workload = generate_workload(120, requests_per_s=1.0, seed=1)
    for policy, kwargs in [("none", {}), ("dynamic", {"max_batch": 8, "max_wait_ms": 50}), ("continuous", {"max_batch": 8})]:
        report = simulate(policy, workload, **kwargs)
        assert sorted(r.request.request_id for r in report.results) == list(range(120))
        assert all(r.finish_ms >= r.first_token_ms >= r.request.arrival_ms for r in report.results)


def test_light_load_batching_matters_less():
    # When requests rarely overlap there is little to batch: throughput is set by arrivals.
    workload = generate_workload(100, requests_per_s=0.05, seed=2, output_tokens_median=40)
    none = simulate("none", workload)
    continuous = simulate("continuous", workload, max_batch=32)
    assert abs(continuous.throughput_requests_per_s - none.throughput_requests_per_s) < 0.01
