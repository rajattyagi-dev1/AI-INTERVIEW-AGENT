"""
LLM provider base — common message/response types and the LLMProvider Protocol.

The interview engine imports ONLY from this module and llm.factory.
It never imports from a concrete provider (openai_provider, groq_provider, etc.)
directly. This is the boundary that allows swapping providers with a single
env-var change.

Usage (interview engine side):
    from llm.factory import get_llm_provider
    from llm.base import LLMMessage, LLMResponse

    llm = get_llm_provider()
    response = llm.chat(messages=[{"role": "user", "content": "Hello"}])
    print(response.content)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# Common message type
# ---------------------------------------------------------------------------

class LLMMessage(dict):
    """
    A single chat message as a plain dict with a constrained shape:
        { "role": "system" | "user" | "assistant", "content": str }

    Implemented as a dict subclass so it can be passed directly to any
    provider's SDK without conversion. Use the helper constructor for
    safety:

        LLMMessage.of("user", "Hello")
    """

    @classmethod
    def of(cls, role: str, content: str) -> "LLMMessage":
        """Construct a validated LLMMessage."""
        if role not in ("system", "user", "assistant"):
            raise ValueError(
                f"Invalid role '{role}'. Must be 'system', 'user', or 'assistant'."
            )
        if not isinstance(content, str):
            raise TypeError(f"content must be str, got {type(content).__name__}")
        msg = cls()
        msg["role"] = role
        msg["content"] = content
        return msg

    @property
    def role(self) -> str:
        return self["role"]

    @property
    def content(self) -> str:
        return self["content"]


# ---------------------------------------------------------------------------
# Common response type
# ---------------------------------------------------------------------------

@dataclass
class LLMResponse:
    """
    Normalised response returned by every provider's chat() method.

    Fields
    ------
    content : str
        The text content of the assistant's reply. For json_mode=True
        calls this will be a JSON string. The caller is responsible for
        parsing it.
    usage : dict
        Token-usage info as reported by the provider. Keys vary by
        provider but commonly include: prompt_tokens, completion_tokens,
        total_tokens. Empty dict if the provider does not report usage.
    model : str
        The model name actually used for this call, as reported by the
        provider. Empty string if not reported.
    provider : str
        Human-readable provider name ("openai", "groq", "anthropic",
        "mock"). Useful for logging and debugging.
    """

    content: str
    usage: dict = field(default_factory=dict)
    model: str = ""
    provider: str = ""


# ---------------------------------------------------------------------------
# LLMProvider Protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class LLMProvider(Protocol):
    """
    Protocol (structural interface) for all LLM providers.

    Any class that implements a chat() method with this exact signature
    satisfies the protocol — no inheritance required.

    Parameters
    ----------
    messages : list[LLMMessage | dict]
        Conversation history in role/content format. Plain dicts are
        accepted for convenience (same shape as LLMMessage).
    json_mode : bool
        If True, instruct the provider to return valid JSON. The caller
        must include a JSON instruction in the system/user prompt as well;
        this flag only sets the API-level parameter.
    temperature : float
        Sampling temperature (0.0 = deterministic, 1.0 = creative).
        Defaults to 0.7 for conversational turns; use lower values for
        structured/feedback generation calls.

    Returns
    -------
    LLMResponse
        Normalised response object. Never raises on a valid API response —
        callers handle errors via exceptions raised by concrete providers.
    """

    def chat(
        self,
        messages: list[dict],
        json_mode: bool = False,
        temperature: float = 0.7,
    ) -> LLMResponse: ...
