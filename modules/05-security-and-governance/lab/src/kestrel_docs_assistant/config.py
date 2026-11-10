"""Settings for the locked-down docs-assistant.

Every value can be overridden with an environment variable prefixed ``KESTREL_``
(e.g. ``KESTREL_LLM_PROVIDER=ollama``). Secrets come from the environment, never
from code or the repo. 📖 See lessons 1.4 (config) and 5.3 (secrets).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# lab/src/kestrel_docs_assistant/config.py -> parents[2] = lab, parents[5] = repo root
LAB_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = Path(__file__).resolve().parents[5]

# A well-known development secret. Fine on your laptop, fatal in production:
# the validator below refuses to start with it when KESTREL_ENV=prod.
DEV_JWT_SECRET = "dev-only-secret-change-me-0123456789abcdef"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="KESTREL_", env_file=".env", extra="ignore")

    env: Literal["dev", "test", "prod"] = "dev"
    data_dir: Path = REPO_ROOT / "datasets"
    registry_dir: Path = LAB_DIR / "registry"
    audit_log_path: Path = LAB_DIR / "artifacts" / "audit.jsonl"

    # --- LLM provider (📖 conventions: fake | ollama | openai) ---
    llm_provider: Literal["fake", "ollama", "openai"] = "fake"
    # "gullible" simulates a model that obeys injected instructions: the worst case.
    # Your defences must hold even against it.
    fake_llm_mode: Literal["extractive", "gullible"] = "gullible"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:1.5b-instruct"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    llm_timeout_s: float = 30.0

    # --- Auth (📖 lesson 5.3) ---
    jwt_secret: str = DEV_JWT_SECRET
    jwt_issuer: str = "kestrel-auth"
    jwt_audience: str = "docs-assistant"
    jwt_ttl_minutes: int = 60

    # --- Abuse limits (📖 lesson 5.1, OWASP LLM10 Unbounded Consumption) ---
    rate_limit_per_minute: int = 30

    # --- Defence layers. Each can be switched off for the "💥 Break it" experiments. ---
    sanitize_ingest: bool = True
    input_guardrails: bool = True
    scan_retrieved_chunks: bool = True
    output_guardrails: bool = True

    @model_validator(mode="after")
    def _no_dev_secret_in_prod(self) -> "Settings":
        if self.env == "prod" and (self.jwt_secret == DEV_JWT_SECRET or len(self.jwt_secret) < 32):
            raise ValueError("Refusing to start: set a strong KESTREL_JWT_SECRET (>= 32 chars) in prod.")
        return self

    @property
    def handbook_dir(self) -> Path:
        return self.data_dir / "handbook"

    @property
    def golden_path(self) -> Path:
        return self.data_dir / "golden" / "handbook_qa.jsonl"


@lru_cache
def get_settings() -> Settings:
    return Settings()
