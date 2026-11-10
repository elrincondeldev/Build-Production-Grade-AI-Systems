"""Settings for the docs-assistant used as the "system under test" in Module 4.

Every value can be overridden with an environment variable prefixed KESTREL_,
e.g. ``KESTREL_LLM_PROVIDER=ollama``. 📖 See lesson 1.4 for why config lives in
the environment and not in code.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

LAB_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = Path(__file__).resolve().parents[5]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="KESTREL_", env_file=".env", extra="ignore")

    # --- LLM -----------------------------------------------------------------
    llm_provider: Literal["fake", "ollama", "openai"] = "fake"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:1.5b-instruct"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-4o-mini"
    llm_timeout_s: float = 60.0

    # --- Data & retrieval ----------------------------------------------------
    data_dir: Path = REPO_ROOT / "datasets"
    top_k: int = 3
    # Strip HTML comments and other hidden text from documents before they reach
    # the prompt. Turning this off is one of the "Break it" experiments.
    sanitize_context: bool = True
    # How many previous user turns are used to understand follow-up questions.
    history_turns: int = 2
    cache_enabled: bool = True

    # --- Prompts -------------------------------------------------------------
    prompt_registry_dir: Path = LAB_DIR / "prompts" / "registry"
    prompt_name: str = "docs_assistant"

    # --- Observability -------------------------------------------------------
    otel_exporter: Literal["console", "otlp", "none"] = "console"
    otlp_endpoint: str = "http://localhost:4318/v1/traces"


@lru_cache
def get_settings() -> Settings:
    return Settings()
