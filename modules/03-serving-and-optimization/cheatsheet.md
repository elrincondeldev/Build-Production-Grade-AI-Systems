# Module 3 cheat sheet: Serving, Inference and Optimization

[Course home](../../README.md) › [Module 3](README.md) › Cheat sheet

## Formulas

| What | Formula | Example |
|---|---|---|
| Arithmetic intensity | FLOPs ÷ bytes moved | Decode ≈ **batch size** FLOPs/byte |
| GPU ridge point | peak FLOP/s ÷ memory bandwidth | H100 ≈ 989 T / 3.35 T ≈ 295 (approx.) |
| Decode speed limit | time/token ≥ model bytes ÷ bandwidth | 8B BF16 (16 GB) on 3.35 TB/s → ≥ 4.8 ms |
| Prefill FLOPs | ≈ 2 × params × prompt tokens | 8B × 2k tokens → 32 TFLOP |
| KV cache per token | 2 × layers × KV heads × head dim × bytes | Llama-3.1-8B-style: 2·32·8·128·2 = **128 KiB** |
| End-to-end latency | queue + TTFT + TPOT × (N_out − 1) | 0.15 s + 0.03 s × 199 ≈ 6.1 s |
| Little's law | L = λ × W | 16 in flight ÷ 8.4 req/s → W ≈ 1.9 s |
| M/M/1 time in system | (1/μ) ÷ (1 − ρ) | ρ = 0.9 → 10× service time |
| Tail amplification | P(≥1 slow of n) = 1 − (1 − p)ⁿ | n = 100, p = 1% → 63% |
| API cost / request | (T_in·p_in + T_out·p_out) ÷ 10⁶ | 1500 in, 200 out, $1/$4 → $0.0023 |
| GPUs needed | ⌈peak weighted tok/s ÷ (measured tok/s × utilization)⌉, ≥ min | |
| Break-even (n GPUs) | (n·GPU$/day + ops$/day) ÷ API$/request | $196 ÷ $0.0023 ≈ 85k req/day |
| Cascade pays off if | p_escalate < 1 − c_small / c_large | small = 1/10 → escalate < 90% |
| Speculative decoding | E[tokens/step] = (1 − α^(k+1)) ÷ (1 − α); speed-up ≈ E ÷ (1 + k·c) | α = 0.8, k = 4, c = 0.05 → ≈ 2.8× |
| Symmetric quantization | q = round(w/s), s = max\|w\| ÷ q_max; error ≤ s/2 | INT8 q_max = 127, INT4 = 7 |

## Prefill vs decode

| | Prefill | Decode |
|---|---|---|
| Bound by | Compute | Memory bandwidth |
| Sets | TTFT | TPOT |
| Speed up with | Prefix caching, shorter prompts, chunked prefill, FP8/W8A8 | Batching, weight quantization, speculative decoding, shorter outputs |

## Choose a serving engine

| Need | Pick |
|---|---|
| Open-weight LLM, many users | **vLLM** |
| Prefix-heavy, agents, JSON outputs | **SGLang** (benchmark vs vLLM) |
| Many model types (tabular, embeddings, vision) | **Triton** (+ ONNX / TensorRT) |
| Python pipeline of models | **Ray Serve** |
| Laptop / edge | **Ollama / llama.cpp** (GGUF) |
| Tiny model in a latency-critical path | **In-process ONNX Runtime** |
| TorchServe | Legacy only: limited maintenance |

## Metrics to report

p50 / p95 / p99 · TTFT · TPOT · throughput (req/s, tok/s) · error rate · **goodput** (requests within SLO) · cost per 1k requests. Always state **throughput at a latency percentile**.

## Caching rules

1. Key = normalised question + **prompt version + model + permission scope + data/index version** + params.
2. TTL + versioned keys + LRU.
3. Prefix caching: always on; put stable prompt parts **first**.
4. Semantic cache: tune the threshold on labelled pairs for **hit precision**; keep it off for money, permissions and personal data.
5. Don't cache personal, time-sensitive, error or high-temperature outputs.

## Batching

None (1 at a time) → **dynamic** (wait ≤ max_wait for ≤ max_batch; great for fixed-shape models) → **continuous** (re-form the batch every decode step; the standard for LLMs).

## Autoscaling signals

✅ queue depth · KV-cache usage · in-flight per replica · TTFT p95 · ❌ CPU % · ❌ GPU "utilization" %. Keep headroom (target ~60–70%), pre-scale for known peaks, shorten cold starts, scale down slowly, shed load gracefully.

## Compression

| Technique | Buys | Costs / watch |
|---|---|---|
| BF16 | Half of FP32, safe range | Baseline |
| Weight-only INT8/INT4 (GPTQ, AWQ, GGUF) | Memory, faster **decode** | Quality at low bits; eval |
| W8A8 / FP8 | Faster compute too | Needs hardware support |
| Unstructured pruning | Fewer non-zeros | No speed-up without sparse kernels |
| Structured pruning | Real speed-up | Accuracy; needs healing |
| Distillation | A small model for a narrow task | Data, training, licences |

## Packaging checklist

Artifact + **sha256** + feature/IO metadata + opset → parity gate → quality gate → latency gate → registry → image (bake / pull / mount) → verify the hash and contract at startup → canary.

**Protobuf:** never reuse field numbers · `reserved` removed fields · add-only changes · version the package · return `model_version`.
