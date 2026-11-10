"""Configuration from environment variables (prefix KESTREL_).

📖 See lesson 0.2. Code reads settings; it never hard-codes URLs, models or keys.
Example:  KESTREL_LLM_PROVIDER=ollama uv run first-llm-call
"""

from __future__ import annotations

from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="KESTREL_", env_file=".env", extra="ignore")

    llm_provider: Literal["fake", "ollama", "openai"] = "fake"
    llm_timeout_s: float = 60.0

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:1.5b-instruct"

    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: SecretStr = SecretStr("")  # SecretStr: never printed in logs or reprs
    openai_model: str = "gpt-4o-mini"
