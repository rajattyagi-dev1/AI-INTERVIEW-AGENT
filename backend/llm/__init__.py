"""
LLM provider package — public re-exports.

Other modules should import from here rather than from submodules:

    from llm import get_llm_provider, LLMProvider, LLMResponse, LLMMessage
    from llm import MockProvider   # tests only
"""

from llm.base import LLMMessage, LLMProvider, LLMResponse
from llm.config import LLMSettings, get_settings
from llm.factory import get_llm_provider
from llm.mock_provider import MockProvider

__all__ = [
    # Protocol and types
    "LLMMessage",
    "LLMProvider",
    "LLMResponse",
    # Config
    "LLMSettings",
    "get_settings",
    # Factory
    "get_llm_provider",
    # Mock (tests)
    "MockProvider",
]
