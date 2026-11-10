"""Settings for the Module 3 service. Every value can be overridden with a KESTREL_* env var."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# lab/src/kestrel_serving/config.py -> parents[5] is the repository root
REPO_ROOT = Path(__file__).resolve().parents[5]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="KESTREL_", env_file=".env", extra="ignore")

    data_dir: Path = REPO_ROOT / "datasets"

    # --- LLM provider (see adapters/llm.py) ---
    llm_provider: Literal["fake", "ollama", "openai"] = "fake"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:1.5b-instruct"
    openai_base_url: str = "http://localhost:8080/v1"
    openai_api_key: str = "not-needed-for-local"
    openai_model: str = "Qwen/Qwen2.5-1.5B-Instruct"
    llm_timeout_s: float = 30.0

    # Simulated cost of the fake LLM. 📖 Lesson 3.2: prefill is parallel (cheap per token),
    # decode is sequential (expensive per token).
    fake_prefill_ms_per_token: float = 0.25
    fake_decode_ms_per_token: float = 12.0
    # How many requests the fake "GPU" serves at once; the rest queue. 0 = unlimited.
    fake_max_concurrency: int = 4

    # --- Embeddings (used by retrieval and the semantic cache) ---
    embeddings_provider: Literal["hash", "sentence-transformers"] = "hash"

    # --- Caching. 📖 Lesson 3.5 ---
    cache_exact_enabled: bool = False
    cache_semantic_enabled: bool = False
    cache_semantic_threshold: float = 0.92
    cache_ttl_s: float = 3600.0
    cache_max_entries: int = 10_000

    # Bump this whenever the prompt template changes: it is part of every cache key,
    # so a new prompt never serves answers produced by the old one.
    prompt_version: str = "v1"
    retrieval_top_k: int = 3


@lru_cache
def get_settings() -> Settings:
    return Settings()
