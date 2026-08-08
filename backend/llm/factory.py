"""
LLM provider factory.

Reads LLM_PROVIDER, LLM_MODEL, and LLM_API_KEY from the environment
(via llm.config.get_settings) and returns the appropriate LLMProvider
instance.

The interview engine and any other caller should obtain a provider
exclusively through this function:

    from llm.factory import get_llm_provider
    llm = get_llm_provider()

The caller never needs to know which concrete class is returned.

Supported providers
-------------------
openai      — OpenAIProvider   (fully implemented)
groq        — GroqProvider     (fully implemented; uses openai SDK)
anthropic   — AnthropicProvider (stub; raises NotImplementedError on chat)
mock        — MockProvider     (for tests; no API key required)
"""

from __future__ import annotations

from llm.base import LLMProvider
from llm.config import LLMSettings


# Lazy imports — concrete providers are only imported when actually needed
# so that a missing openai package only fails when OpenAI is selected.

def get_llm_provider(settings: LLMSettings | None = None) -> LLMProvider:
    """
    Instantiate and return the configured LLM provider.

    Parameters
    ----------
    settings : LLMSettings | None
        Optional settings override. If None, reads from the environment
        via get_settings(). Pass an explicit LLMSettings in tests to
        avoid touching the real .env file.

    Returns
    -------
    LLMProvider
        A concrete provider that satisfies the LLMProvider Protocol.

    Raises
    ------
    ValueError
        If LLM_PROVIDER is not one of the recognised values.
    ValueError
        If the provider requires an API key and LLM_API_KEY is empty.
    """
    if settings is None:
        from llm.config import get_settings
        settings = get_settings()

    provider_name = settings.LLM_PROVIDER.lower().strip()
    model = settings.LLM_MODEL
    api_key = settings.LLM_API_KEY

    match provider_name:
        case "openai":
            from llm.openai_provider import OpenAIProvider
            return OpenAIProvider(api_key=api_key, model=model)

        case "groq":
            from llm.groq_provider import GroqProvider
            return GroqProvider(api_key=api_key, model=model)

        case "anthropic":
            from llm.anthropic_provider import AnthropicProvider
            return AnthropicProvider(api_key=api_key, model=model)

        case "mock":
            from llm.mock_provider import MockProvider
            return MockProvider()

        case _:
            supported = "openai, groq, anthropic, mock"
            raise ValueError(
                f"Unknown LLM provider: '{provider_name}'. "
                f"Supported providers: {supported}. "
                f"Set LLM_PROVIDER in backend/.env."
            )
