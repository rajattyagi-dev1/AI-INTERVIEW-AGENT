"""
Anthropic provider — stub implementation.

Anthropic's API differs structurally from the OpenAI API (different
message shapes, separate system prompt parameter, different response
object). Implementing it properly requires the anthropic Python SDK.

This stub raises NotImplementedError to signal it is not yet wired,
but it fits the LLMProvider Protocol signature so the factory can
return it and tests can verify the provider name.

To activate in a future task:
    pip install anthropic>=0.30.0
    LLM_PROVIDER=anthropic
    LLM_MODEL=claude-3-5-sonnet-20241022
    LLM_API_KEY=<your-anthropic-api-key>

Anthropic model examples:
    claude-3-5-sonnet-20241022   (recommended for production)
    claude-3-5-haiku-20241022    (fast, cost-effective)
    claude-3-opus-20240229       (most capable)
"""

from __future__ import annotations

from llm.base import LLMResponse


class AnthropicProvider:
    """
    Stub LLM provider for Anthropic Claude.

    Not yet implemented. Raises NotImplementedError on chat().
    Requires the anthropic SDK when implemented.
    """

    PROVIDER_NAME = "anthropic"

    def __init__(self, api_key: str, model: str) -> None:
        if not api_key:
            raise ValueError(
                "Anthropic API key is required. "
                "Set LLM_API_KEY in backend/.env or the environment."
            )
        self._api_key = api_key
        self._model = model

    def chat(
        self,
        messages: list[dict],
        json_mode: bool = False,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """
        Not yet implemented.

        To implement: install anthropic SDK, translate messages to the
        Anthropic format (separate system message, content blocks), call
        client.messages.create(), and map the response to LLMResponse.
        """
        raise NotImplementedError(
            "AnthropicProvider is not yet implemented. "
            "Set LLM_PROVIDER=openai or LLM_PROVIDER=groq instead."
        )
