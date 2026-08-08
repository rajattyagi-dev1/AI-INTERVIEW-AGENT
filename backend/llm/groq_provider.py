"""
Groq provider — stub implementation.

Groq exposes an OpenAI-compatible API endpoint. This stub can be
activated by switching to the openai SDK pointed at Groq's base URL.
No new dependencies are introduced — the existing openai package is
reused with a custom base_url.

To use this provider:
    LLM_PROVIDER=groq
    LLM_MODEL=llama-3.3-70b-versatile
    LLM_API_KEY=<your-groq-api-key>

The stub raises NotImplementedError until fleshed out in a future task.
Groq model examples:
    llama-3.3-70b-versatile
    llama-3.1-8b-instant
    mixtral-8x7b-32768
"""

from __future__ import annotations

from openai import OpenAI

from llm.base import LLMResponse

_GROQ_BASE_URL = "https://api.groq.com/openai/v1"


class GroqProvider:
    """
    Stub LLM provider for Groq.

    Uses the openai SDK with Groq's OpenAI-compatible endpoint.
    No additional packages required beyond openai>=1.0.0.
    """

    PROVIDER_NAME = "groq"

    def __init__(self, api_key: str, model: str) -> None:
        if not api_key:
            raise ValueError(
                "Groq API key is required. "
                "Set LLM_API_KEY in backend/.env or the environment."
            )
        self._client = OpenAI(api_key=api_key, base_url=_GROQ_BASE_URL)
        self._model = model

    def chat(
        self,
        messages: list[dict],
        json_mode: bool = False,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """
        Send a chat completion request to the Groq API.

        Note: Groq's JSON mode support varies by model. If json_mode=True
        and the model does not support it, the API may return an error.
        In that case, rely on prompt-level JSON instructions instead.
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
