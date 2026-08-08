"""
Mock LLM provider for unit and integration tests.

Returns deterministic, configurable responses without making any
network call. The interview engine tests use this exclusively so
they run offline and cost nothing.

Usage in tests:
    from llm.mock_provider import MockProvider

    # Returns a fixed string for every call
    llm = MockProvider(response="Hello from mock")
    resp = llm.chat([{"role": "user", "content": "Hi"}])
    assert resp.content == "Hello from mock"

    # Tracks all calls for assertion
    assert llm.call_count == 1
    assert llm.last_messages[0]["role"] == "user"

    # Raises on demand (to test error handling)
    llm = MockProvider(raises=ValueError("simulated failure"))
    with pytest.raises(ValueError):
        llm.chat([...])
"""

from __future__ import annotations

from typing import Optional
from llm.base import LLMResponse


class MockProvider:
    """
    Deterministic mock LLM provider for tests.

    Satisfies the LLMProvider Protocol without any network calls.
    """

    PROVIDER_NAME = "mock"

    def __init__(
        self,
        response: str = '{"reply": "Mock interviewer response.", "wants_followup": false, "followup_reason": ""}',
        raises: Optional[Exception] = None,
        model: str = "mock-model",
    ) -> None:
        """
        Parameters
        ----------
        response : str
            The content string returned by every chat() call.
            Defaults to a valid TurnResponse JSON so it works out-of-the-box
            with the interview engine's JSON parsing (Task 6+).
        raises : Exception | None
            If set, chat() raises this exception instead of returning.
            Used to test error-handling paths.
        model : str
            The model name reported in LLMResponse.model.
        """
        self._response = response
        self._raises = raises
        self._model = model

        # Call tracking — inspectable in tests
        self.call_count: int = 0
        self.last_messages: list[dict] = []
        self.last_json_mode: bool = False
        self.last_temperature: float = 0.7

    def chat(
        self,
        messages: list[dict],
        json_mode: bool = False,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """
        Return the configured mock response (or raise the configured exception).

        Records all call parameters for test assertions.
        """
        self.call_count += 1
        self.last_messages = list(messages)
        self.last_json_mode = json_mode
        self.last_temperature = temperature

        if self._raises is not None:
            raise self._raises

        return LLMResponse(
            content=self._response,
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            model=self._model,
            provider=self.PROVIDER_NAME,
        )

    def reset(self) -> None:
        """Reset call tracking between test cases."""
        self.call_count = 0
        self.last_messages = []
        self.last_json_mode = False
        self.last_temperature = 0.7
