"""
LLM configuration via environment variables.

Uses pydantic-settings so values are automatically read from the .env
file (already gitignored) or from the process environment.

All other modules obtain config via:
    from llm.config import get_settings
    settings = get_settings()
"""

from __future__ import annotations

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseSettings):
    """
    Environment-variable–backed LLM configuration.

    Variables (set in backend/.env):
        LLM_PROVIDER   — which provider to use: openai | groq | anthropic | gemini | mock
        LLM_MODEL      — model name for the chosen provider
        LLM_API_KEY    — API key (never committed to source control)

    The .env file is loaded from the directory where the backend process
    runs (i.e. backend/).  pydantic-settings searches for .env in the
    current working directory by default.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",      # ignore unrelated env vars
    )

    LLM_PROVIDER: str = "openai"
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_API_KEY: str = ""


@lru_cache(maxsize=1)
def get_settings() -> LLMSettings:
    """
    Return the cached LLMSettings instance.

    lru_cache ensures the .env file is read only once per process.
    Call get_settings.cache_clear() in tests to reset between test cases.
    """
    return LLMSettings()
