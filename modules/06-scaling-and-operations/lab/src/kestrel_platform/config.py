"""Settings for the platform service. Everything is configured via KESTREL_* env vars.

📖 See lesson 1.4 (configuration and secrets) and lesson 6.4 (fault injection for canaries).
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="KESTREL_", env_file=".env", extra="ignore")

    app_name: str = "kestrel-platform"
    # The version label is what lets you tell "stable" from "canary" in metrics.
    app_version: str = "v1"
    log_level: str = "INFO"

    # Fault injection: lets you *simulate* a bad release locally and watch the
    # canary analysis catch it. Never enable these in a real production config.
    fault_error_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    fault_extra_latency_ms: float = Field(default=0.0, ge=0.0)
    fault_seed: int = 0

    # Readiness can be flipped off to drain a pod before shutdown (lesson 6.1).
    ready: bool = True

    # Secret example: injected from a Kubernetes Secret, never from a ConfigMap.
    api_token: str | None = None

    # LLM adapter (used by the optional LLM planner of the refund agent).
    llm_provider: str = "fake"  # fake | ollama | openai
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:1.5b-instruct"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def find_repo_root(start: Path | None = None) -> Path:
    """Walk up from this file until we find the course repo root (it has `datasets/`).

    Labs are self-contained, but the shared datasets live at the repo root.
    `KESTREL_DATA_DIR` overrides the datasets location if you moved things around.
    """
    here = (start or Path(__file__)).resolve()
    for parent in [here, *here.parents]:
        if (parent / "datasets" / "handbook").is_dir():
            return parent
    raise FileNotFoundError("Could not find the course repo root (a folder containing datasets/handbook).")


def datasets_dir() -> Path:
    override = os.environ.get("KESTREL_DATA_DIR")
    return Path(override) if override else find_repo_root() / "datasets"
