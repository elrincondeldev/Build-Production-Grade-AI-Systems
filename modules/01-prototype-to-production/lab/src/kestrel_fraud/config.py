"""Typed configuration loaded from environment variables (📖 lesson 1.4).

Twelve-Factor rule: config lives in the environment, not in code. pydantic-settings
reads every field from an env var with the ``KESTREL_`` prefix and validates it at
startup, so a typo in a threshold fails fast instead of at 3 a.m.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LAB_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="KESTREL_", env_file=".env", extra="ignore")

    # --- service identity -------------------------------------------------
    service_name: str = "fraud-service"
    environment: Literal["dev", "test", "staging", "prod"] = "dev"
    log_level: str = "INFO"
    log_json: bool = True

    # --- model artifact ---------------------------------------------------
    model_dir: Path = LAB_ROOT / "artifacts" / "fraud-model"
    model_version: str = "latest"

    # --- decision policy ----------------------------------------------------
    review_threshold: float = Field(0.30, ge=0.0, le=1.0)
    decline_threshold: float = Field(0.80, ge=0.0, le=1.0)

    # --- enrichment (online feature store) ----------------------------------
    enrichment_base_url: str | None = None
    enrichment_timeout_s: float = Field(0.3, gt=0)
    enrichment_max_attempts: int = Field(3, ge=1, le=10)
    enrichment_deadline_s: float = Field(1.0, gt=0)
    retry_budget_ratio: float = Field(0.1, ge=0.0, le=1.0)

    # --- LLM for /v1/explain ------------------------------------------------
    llm_provider: Literal["fake", "ollama", "openai"] = "fake"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:1.5b-instruct"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    # SecretStr hides the value in repr() and logs: print(settings) shows '**********'.
    openai_api_key: SecretStr | None = None
    llm_timeout_s: float = Field(30.0, gt=0)

    @model_validator(mode="after")
    def _thresholds_are_ordered(self) -> Settings:
        if self.review_threshold > self.decline_threshold:
            raise ValueError("review_threshold must be <= decline_threshold")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
