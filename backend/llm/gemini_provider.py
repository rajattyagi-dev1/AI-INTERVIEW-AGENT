"""
Gemini provider — implementation using Google Gemini's OpenAI-compatible API.

Gemini exposes an OpenAI-compatible REST endpoint at:
    https://generativelanguage.googleapis.com/v1beta/openai/

No new dependencies are introduced — the existing openai package is
reused with Gemini's base URL.

To use this provider:
    LLM_PROVIDER=gemini
    LLM_MODEL=gemini-2.5-flash
    LLM_API_KEY=<your-gemini-api-key>

Gemini model examples:
    gemini-2.5-flash
    gemini-2.5-pro
"""

from __future__ import annotations

from openai import OpenAI

from llm.base import LLMResponse

_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


class GeminiProvider:
    """
    LLM provider for Google Gemini using its OpenAI-compatible endpoint.

    Satisfies the LLMProvider Protocol defined in llm.base.
    """

    PROVIDER_NAME = "gemini"

    def __init__(self, api_key: str, model: str) -> None:
        if not api_key:
            raise ValueError(
                "Gemini API key is required. "
                "Set LLM_API_KEY in backend/.env or the environment."
            )
        self._client = OpenAI(api_key=api_key, base_url=_GEMINI_BASE_URL)
        self._model = model

    def chat(
        self,
        messages: list[dict],
        json_mode: bool = False,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """
        Send a chat completion request to the Gemini OpenAI-compatible API.
        """
        kwargs: dict = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        completion = self._client.chat.completions.create(**kwargs)

        content = completion.choices[0].message.content or ""
        usage = {}
        if completion.usage:
            usage = {
                "prompt_tokens": completion.usage.prompt_tokens,
                "completion_tokens": completion.usage.completion_tokens,
                "total_tokens": completion.usage.total_tokens,
            }

        return LLMResponse(
            content=content,
            usage=usage,
            model=completion.model,
            provider=self.PROVIDER_NAME,
        )
