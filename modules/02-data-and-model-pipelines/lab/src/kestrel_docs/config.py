"""All configuration comes from environment variables prefixed with KESTREL_ (📖 lesson 1.4)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "datasets" / "handbook").is_dir():
            return parent
    raise FileNotFoundError("Could not find datasets/handbook. Set KESTREL_HANDBOOK_DIR.")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="KESTREL_", env_file=".env", extra="ignore")

    # Data
    handbook_dir: Path | None = None
    golden_path: Path | None = None

    # Providers (fake/hash need no network, no keys: tests and CI use them)
    llm_provider: Literal["fake", "ollama", "openai"] = "fake"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:1.5b-instruct"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    llm_timeout_s: float = 30.0
    embeddings_provider: Literal["hash", "sentence-transformers"] = "hash"
    embeddings_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    reranker: Literal["lexical", "cross-encoder", "none"] = "lexical"

    # Chunking (characters) and retrieval
    chunk_size: int = 600
    chunk_overlap: int = 100
    candidates_per_retriever: int = 20
    top_k: int = 4
    context_token_budget: int = 900

    def resolved_handbook_dir(self) -> Path:
        return self.handbook_dir or _find_repo_root() / "datasets" / "handbook"

    def resolved_golden_path(self) -> Path:
        return self.golden_path or _find_repo_root() / "datasets" / "golden" / "handbook_qa.jsonl"


@lru_cache
def get_settings() -> Settings:
    return Settings()
