"""
OpenAI provider — real implementation backed by the openai Python SDK.

Satisfies the LLMProvider Protocol defined in llm.base.

The provider is intentionally thin: it translates the common
LLMMessage/LLMResponse types to/from the OpenAI SDK types and passes
control straight through. All retry/error handling is the caller's
responsibility (the interview engine layer handles retries).

Requires:
    pip install openai>=1.0.0
    LLM_API_KEY set to a valid OpenAI API key
"""

from __future__ import annotations

from openai import OpenAI

from llm.base import LLMResponse


class OpenAIProvider:
    """
    Chat completion provider backed by the OpenAI API.

    Supports:
        - Standard chat completions (any GPT-4o / GPT-4 / GPT-3.5 model)
        - JSON mode (response_format={"type": "json_object"})
        - Configurable temperature
    """

    PROVIDER_NAME = "openai"

    def __init__(self, api_key: str, model: str) -> None:
        if not api_key:
            raise ValueError(
                "OpenAI API key is required. "
                "Set LLM_API_KEY in backend/.env or the environment."
            )
        self._client = OpenAI(api_key=api_key)
        self._model = model

    def chat(
        self,
        messages: list[dict],
        json_mode: bool = False,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """
        Send a chat completion request to the OpenAI API.

        Parameters
        ----------
        messages : list[dict]
            Role/content dicts. Accepts LLMMessage instances or plain dicts.
        json_mode : bool
            If True, sets response_format={"type": "json_object"}.
            The caller must include a JSON instruction in the messages.
        temperature : float
            Sampling temperature.

        Returns
        -------
        LLMResponse
            Normalised response with content, usage, model, and provider.

        Raises
        ------
        openai.APIError and subclasses on API failures.
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
