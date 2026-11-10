"""CLI: your first LLM call.

    uv run first-llm-call                                  # fake model, no network
    uv run first-llm-call --provider ollama                # local model via Ollama
    uv run first-llm-call --provider ollama --stream       # tokens as they arrive
    uv run first-llm-call --prompt "Explain a chargeback in one sentence."
"""

from __future__ import annotations

import argparse
import asyncio
import time

from .config import Settings
from .llm import Message, estimate_cost_usd, get_llm

SYSTEM_PROMPT = "You are a concise assistant for Kestrel Pay employees. Answer in at most two sentences."

# ⚠️ Illustrative prices in USD per 1M tokens, NOT current list prices.
# Prices change often: always check the provider's pricing page.
EXAMPLE_PRICES = {
    "small hosted model": (0.15, 0.60),
    "large hosted model": (2.50, 10.00),
}


async def run(provider: str, prompt: str, stream: bool, temperature: float) -> None:
    settings = Settings(llm_provider=provider)  # type: ignore[arg-type]
    llm = get_llm(settings)
    messages = [Message("system", SYSTEM_PROMPT), Message("user", prompt)]

    if stream:
        start = time.perf_counter()
        first_token_ms: float | None = None
        print("assistant> ", end="", flush=True)
        async for piece in llm.stream(messages, temperature=temperature):
            if first_token_ms is None:
                first_token_ms = (time.perf_counter() - start) * 1000
            print(piece, end="", flush=True)
        total_ms = (time.perf_counter() - start) * 1000
        print(f"\n\ntime to first token: {first_token_ms or 0:.0f} ms · total: {total_ms:.0f} ms")
        return

    c = await llm.complete(messages, temperature=temperature)
    print(f"assistant> {c.text}\n")
    print(f"model={c.model}  prompt_tokens={c.prompt_tokens}  completion_tokens={c.completion_tokens}  latency={c.latency_ms:.0f} ms")
    print("\nWhat would 1,000,000 calls like this cost? (illustrative prices)")
    for name, (inp, out) in EXAMPLE_PRICES.items():
        per_call = estimate_cost_usd(c.prompt_tokens, c.completion_tokens, inp, out)
        print(f"  {name:<20} ${per_call * 1_000_000:>10,.2f}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Your first LLM call (Lab 0).")
    parser.add_argument("--provider", choices=["fake", "ollama", "openai"], default=None,
                        help="defaults to KESTREL_LLM_PROVIDER or 'fake'")
    parser.add_argument("--prompt", default="What is a card chargeback?")
    parser.add_argument("--stream", action="store_true")
    parser.add_argument("--temperature", type=float, default=0.0)
    args = parser.parse_args(argv)
    provider = args.provider or Settings().llm_provider
    asyncio.run(run(provider, args.prompt, args.stream, args.temperature))


if __name__ == "__main__":
    main()
