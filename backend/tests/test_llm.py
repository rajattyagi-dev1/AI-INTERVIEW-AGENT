"""
Unit tests for the LLM provider abstraction layer (llm/).

Tests are fully offline — no real API calls are made.
The openai SDK is present in the venv but all provider instantiation
that would call the network is mocked or avoided.

Test groups:
  TestLLMMessage          — LLMMessage construction and validation
  TestLLMResponse         — LLMResponse dataclass defaults and fields
  TestLLMProviderProtocol — Protocol structural conformance
  TestMockProvider        — MockProvider behaviour and call tracking
  TestFactory             — Factory provider selection and error handling
  TestConfig              — LLMSettings defaults and env-var override
  TestOpenAIProviderInit  — OpenAIProvider construction (no real API call)
  TestStubProviders       — Anthropic/Groq init and expected errors
"""

from __future__ import annotations

import os
import pytest
from unittest.mock import patch, MagicMock

from llm.base import LLMMessage, LLMResponse, LLMProvider
from llm.mock_provider import MockProvider
from llm.config import LLMSettings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_settings(**overrides) -> LLMSettings:
    """Build an LLMSettings with test defaults, overridable by kwargs."""
    defaults = {
        "LLM_PROVIDER": "mock",
        "LLM_MODEL": "mock-model",
        "LLM_API_KEY": "",
    }
    defaults.update(overrides)
    return LLMSettings.model_validate(defaults)


# ---------------------------------------------------------------------------
# TestLLMMessage
# ---------------------------------------------------------------------------

class TestLLMMessage:
    def test_of_creates_user_message(self):
        msg = LLMMessage.of("user", "Hello")
        assert msg["role"] == "user"
        assert msg["content"] == "Hello"

    def test_of_creates_system_message(self):
        msg = LLMMessage.of("system", "You are an interviewer.")
        assert msg.role == "system"
        assert msg.content == "You are an interviewer."

    def test_of_creates_assistant_message(self):
        msg = LLMMessage.of("assistant", "Good answer.")
        assert msg.role == "assistant"

    def test_invalid_role_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid role"):
            LLMMessage.of("invalid_role", "content")

    def test_non_string_content_raises_type_error(self):
        with pytest.raises(TypeError):
            LLMMessage.of("user", 123)  # type: ignore

    def test_message_is_dict_subclass(self):
        msg = LLMMessage.of("user", "Hi")
        assert isinstance(msg, dict)

    def test_message_can_be_used_as_plain_dict(self):
        msg = LLMMessage.of("user", "Hi")
        assert msg.get("role") == "user"
        assert msg.get("content") == "Hi"

    def test_role_property(self):
        msg = LLMMessage.of("system", "Sys prompt")
        assert msg.role == "system"

    def test_content_property(self):
        msg = LLMMessage.of("user", "My answer")
        assert msg.content == "My answer"


# ---------------------------------------------------------------------------
# TestLLMResponse
# ---------------------------------------------------------------------------

class TestLLMResponse:
    def test_required_content_field(self):
        r = LLMResponse(content="Hello")
        assert r.content == "Hello"

    def test_defaults(self):
        r = LLMResponse(content="Hi")
        assert r.usage == {}
        assert r.model == ""
        assert r.provider == ""

    def test_full_construction(self):
        r = LLMResponse(
            content="Answer",
            usage={"prompt_tokens": 5, "completion_tokens": 10, "total_tokens": 15},
            model="gpt-4o-mini",
            provider="openai",
        )
        assert r.usage["total_tokens"] == 15
        assert r.model == "gpt-4o-mini"
        assert r.provider == "openai"

    def test_content_is_string(self):
        r = LLMResponse(content="test")
        assert isinstance(r.content, str)


# ---------------------------------------------------------------------------
# TestLLMProviderProtocol
# ---------------------------------------------------------------------------

class TestLLMProviderProtocol:
    """Verify structural Protocol conformance via isinstance checks."""

    def test_mock_provider_satisfies_protocol(self):
        mock = MockProvider()
        assert isinstance(mock, LLMProvider)

    def test_class_without_chat_does_not_satisfy_protocol(self):
        class NotAProvider:
            pass
        assert not isinstance(NotAProvider(), LLMProvider)

    def test_class_with_chat_satisfies_protocol(self):
        class MinimalProvider:
            def chat(self, messages, json_mode=False, temperature=0.7):
                return LLMResponse(content="ok")
        assert isinstance(MinimalProvider(), LLMProvider)

    def test_openai_provider_satisfies_protocol_when_instantiated(self):
        with patch("llm.openai_provider.OpenAI") as mock_openai_cls:
            mock_openai_cls.return_value = MagicMock()
            from llm.openai_provider import OpenAIProvider
            provider = OpenAIProvider(api_key="sk-test", model="gpt-4o-mini")
            assert isinstance(provider, LLMProvider)

    def test_anthropic_provider_satisfies_protocol(self):
        from llm.anthropic_provider import AnthropicProvider
        p = AnthropicProvider(api_key="test-key", model="claude-3-5-sonnet-20241022")
        assert isinstance(p, LLMProvider)

    def test_groq_provider_satisfies_protocol_structurally(self):
        # GroqProvider has a chat() method — it satisfies the Protocol structurally
        # even without instantiating (which would require the openai package and key).
        from llm.groq_provider import GroqProvider
        import inspect
        assert hasattr(GroqProvider, "chat")
        sig = inspect.signature(GroqProvider.chat)
        assert "messages" in sig.parameters
        assert "json_mode" in sig.parameters
        assert "temperature" in sig.parameters


# ---------------------------------------------------------------------------
# TestMockProvider
# ---------------------------------------------------------------------------

class TestMockProvider:
    def test_returns_configured_response(self):
        mock = MockProvider(response="Test reply")
        result = mock.chat([LLMMessage.of("user", "Hi")])
        assert result.content == "Test reply"

    def test_provider_name_is_mock(self):
        mock = MockProvider()
        result = mock.chat([])
        assert result.provider == "mock"

    def test_model_name_reported(self):
        mock = MockProvider(model="test-model-v1")
        result = mock.chat([])
        assert result.model == "test-model-v1"

    def test_usage_is_populated(self):
        mock = MockProvider()
        result = mock.chat([])
        assert result.usage["total_tokens"] == 30

    def test_call_count_increments(self):
        mock = MockProvider()
        mock.chat([])
        mock.chat([])
        assert mock.call_count == 2

    def test_last_messages_recorded(self):
        mock = MockProvider()
        msgs = [LLMMessage.of("user", "Question?")]
        mock.chat(msgs)
        assert mock.last_messages[0]["role"] == "user"
        assert mock.last_messages[0]["content"] == "Question?"

    def test_json_mode_recorded(self):
        mock = MockProvider()
        mock.chat([], json_mode=True)
        assert mock.last_json_mode is True

    def test_temperature_recorded(self):
        mock = MockProvider()
        mock.chat([], temperature=0.2)
        assert mock.last_temperature == 0.2

    def test_raises_configured_exception(self):
        mock = MockProvider(raises=ValueError("simulated API failure"))
        with pytest.raises(ValueError, match="simulated API failure"):
            mock.chat([])

    def test_call_count_still_increments_on_raise(self):
        mock = MockProvider(raises=RuntimeError("boom"))
        with pytest.raises(RuntimeError):
            mock.chat([])
        assert mock.call_count == 1

    def test_reset_clears_call_tracking(self):
        mock = MockProvider()
        mock.chat([LLMMessage.of("user", "Hello")])
        mock.reset()
        assert mock.call_count == 0
        assert mock.last_messages == []
        assert mock.last_json_mode is False

    def test_default_response_is_valid_json_string(self):
        import json
        mock = MockProvider()
        result = mock.chat([])
        parsed = json.loads(result.content)
        assert "reply" in parsed

    def test_plain_dict_messages_accepted(self):
        mock = MockProvider()
        result = mock.chat([{"role": "user", "content": "plain dict"}])
        assert result.content is not None


# ---------------------------------------------------------------------------
# TestFactory
# ---------------------------------------------------------------------------

class TestFactory:
    """Factory tests use explicit LLMSettings to avoid touching .env."""

    def test_mock_provider_selected(self):
        from llm.factory import get_llm_provider
        settings = _make_settings(LLM_PROVIDER="mock")
        provider = get_llm_provider(settings=settings)
        assert isinstance(provider, MockProvider)

    def test_mock_provider_name(self):
        from llm.factory import get_llm_provider
        settings = _make_settings(LLM_PROVIDER="mock")
        provider = get_llm_provider(settings=settings)
        result = provider.chat([])
        assert result.provider == "mock"

    def test_unknown_provider_raises_value_error(self):
        from llm.factory import get_llm_provider
        settings = _make_settings(LLM_PROVIDER="unknown_provider_xyz")
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            get_llm_provider(settings=settings)

    def test_unknown_provider_error_lists_supported(self):
        from llm.factory import get_llm_provider
        settings = _make_settings(LLM_PROVIDER="cohere")
        with pytest.raises(ValueError) as exc_info:
            get_llm_provider(settings=settings)
        assert "openai" in str(exc_info.value)
        assert "groq" in str(exc_info.value)
        assert "anthropic" in str(exc_info.value)
        assert "gemini" in str(exc_info.value)

    def test_openai_provider_selected_by_name(self):
        from llm.factory import get_llm_provider
        from llm.openai_provider import OpenAIProvider
        settings = _make_settings(LLM_PROVIDER="openai", LLM_API_KEY="sk-test")
        with patch.object(OpenAIProvider, "__init__", return_value=None):
            provider = get_llm_provider(settings=settings)
            assert isinstance(provider, OpenAIProvider)

    def test_groq_provider_selected_by_name(self):
        from llm.factory import get_llm_provider
        from llm.groq_provider import GroqProvider
        settings = _make_settings(LLM_PROVIDER="groq", LLM_API_KEY="gsk-test")
        with patch.object(GroqProvider, "__init__", return_value=None):
            provider = get_llm_provider(settings=settings)
            assert isinstance(provider, GroqProvider)

    def test_gemini_provider_selected_by_name(self):
        from llm.factory import get_llm_provider
        from llm.gemini_provider import GeminiProvider
        settings = _make_settings(LLM_PROVIDER="gemini", LLM_API_KEY="gem-test")
        with patch.object(GeminiProvider, "__init__", return_value=None):
            provider = get_llm_provider(settings=settings)
            assert isinstance(provider, GeminiProvider)

    def test_anthropic_provider_selected_by_name(self):
        from llm.factory import get_llm_provider
        from llm.anthropic_provider import AnthropicProvider
        settings = _make_settings(LLM_PROVIDER="anthropic", LLM_API_KEY="ant-test")
        provider = get_llm_provider(settings=settings)
        assert isinstance(provider, AnthropicProvider)

    def test_provider_name_case_insensitive(self):
        from llm.factory import get_llm_provider
        settings = _make_settings(LLM_PROVIDER="MOCK")
        provider = get_llm_provider(settings=settings)
        assert isinstance(provider, MockProvider)

    def test_provider_name_strips_whitespace(self):
        from llm.factory import get_llm_provider
        settings = _make_settings(LLM_PROVIDER="  mock  ")
        provider = get_llm_provider(settings=settings)
        assert isinstance(provider, MockProvider)

    def test_openai_missing_api_key_raises(self):
        from llm.factory import get_llm_provider
        settings = _make_settings(LLM_PROVIDER="openai", LLM_API_KEY="")
        with pytest.raises(ValueError, match="API key"):
            get_llm_provider(settings=settings)

    def test_groq_missing_api_key_raises(self):
        from llm.factory import get_llm_provider
        settings = _make_settings(LLM_PROVIDER="groq", LLM_API_KEY="")
        with pytest.raises(ValueError, match="API key"):
            get_llm_provider(settings=settings)

    def test_anthropic_missing_api_key_raises(self):
        from llm.factory import get_llm_provider
        settings = _make_settings(LLM_PROVIDER="anthropic", LLM_API_KEY="")
        with pytest.raises(ValueError, match="API key"):
            get_llm_provider(settings=settings)

    def test_mock_does_not_require_api_key(self):
        from llm.factory import get_llm_provider
        settings = _make_settings(LLM_PROVIDER="mock", LLM_API_KEY="")
        provider = get_llm_provider(settings=settings)  # must not raise
        assert provider is not None


# ---------------------------------------------------------------------------
# TestConfig
# ---------------------------------------------------------------------------

class TestConfig:
    def test_defaults(self):
        # Construct directly from dict to avoid .env file side-effects.
        s = LLMSettings.model_validate({
            "LLM_PROVIDER": "openai",
            "LLM_MODEL": "gpt-4o-mini",
            "LLM_API_KEY": "",
        })
        assert s.LLM_PROVIDER == "openai"
        assert s.LLM_MODEL == "gpt-4o-mini"
        assert s.LLM_API_KEY == ""

    def test_override_provider(self):
        s = LLMSettings.model_validate({
            "LLM_PROVIDER": "groq",
            "LLM_MODEL": "llama-3.3-70b-versatile",
            "LLM_API_KEY": "test-key",
        })
        assert s.LLM_PROVIDER == "groq"
        assert s.LLM_MODEL == "llama-3.3-70b-versatile"

    def test_api_key_stored(self):
        s = LLMSettings.model_validate({
            "LLM_PROVIDER": "openai",
            "LLM_MODEL": "gpt-4o",
            "LLM_API_KEY": "sk-test-12345",
        })
        assert s.LLM_API_KEY == "sk-test-12345"

    def test_extra_keys_ignored(self):
        # extra="ignore" in model_config — should not raise
        s = LLMSettings.model_validate({
            "LLM_PROVIDER": "mock",
            "LLM_MODEL": "mock-model",
            "LLM_API_KEY": "",
            "SOME_UNRELATED_KEY": "value",
        })
        assert s.LLM_PROVIDER == "mock"


# ---------------------------------------------------------------------------
# TestOpenAIProviderInit
# ---------------------------------------------------------------------------

class TestOpenAIProviderInit:
    """Test OpenAIProvider construction without making real API calls."""

    def test_raises_if_api_key_empty(self):
        from llm.openai_provider import OpenAIProvider
        with pytest.raises(ValueError, match="API key"):
            OpenAIProvider(api_key="", model="gpt-4o-mini")

    def test_constructs_with_valid_key(self):
        from llm.openai_provider import OpenAIProvider
        with patch("llm.openai_provider.OpenAI") as mock_openai:
            mock_openai.return_value = MagicMock()
            provider = OpenAIProvider(api_key="sk-test", model="gpt-4o-mini")
            assert provider is not None
            mock_openai.assert_called_once_with(api_key="sk-test")

    def test_provider_name_constant(self):
        from llm.openai_provider import OpenAIProvider
        assert OpenAIProvider.PROVIDER_NAME == "openai"

    def test_chat_returns_llm_response(self):
        from llm.openai_provider import OpenAIProvider
        mock_completion = MagicMock()
        mock_completion.choices[0].message.content = "Mocked response"
        mock_completion.model = "gpt-4o-mini"
        mock_completion.usage.prompt_tokens = 10
        mock_completion.usage.completion_tokens = 20
        mock_completion.usage.total_tokens = 30

        with patch("llm.openai_provider.OpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_completion
            mock_openai_cls.return_value = mock_client

            provider = OpenAIProvider(api_key="sk-test", model="gpt-4o-mini")
            result = provider.chat([LLMMessage.of("user", "Hello")])

        assert isinstance(result, LLMResponse)
        assert result.content == "Mocked response"
        assert result.provider == "openai"
        assert result.usage["total_tokens"] == 30

    def test_json_mode_sets_response_format(self):
        from llm.openai_provider import OpenAIProvider
        mock_completion = MagicMock()
        mock_completion.choices[0].message.content = '{"key": "value"}'
        mock_completion.model = "gpt-4o-mini"
        mock_completion.usage.prompt_tokens = 5
        mock_completion.usage.completion_tokens = 10
        mock_completion.usage.total_tokens = 15

        with patch("llm.openai_provider.OpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_completion
            mock_openai_cls.return_value = mock_client

            provider = OpenAIProvider(api_key="sk-test", model="gpt-4o-mini")
            provider.chat([LLMMessage.of("user", "Return JSON")], json_mode=True)

            call_kwargs = mock_client.chat.completions.create.call_args.kwargs
            assert call_kwargs["response_format"] == {"type": "json_object"}

    def test_temperature_passed_through(self):
        from llm.openai_provider import OpenAIProvider
        mock_completion = MagicMock()
        mock_completion.choices[0].message.content = "response"
        mock_completion.model = "gpt-4o-mini"
        mock_completion.usage.prompt_tokens = 1
        mock_completion.usage.completion_tokens = 1
        mock_completion.usage.total_tokens = 2

        with patch("llm.openai_provider.OpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_completion
            mock_openai_cls.return_value = mock_client

            provider = OpenAIProvider(api_key="sk-test", model="gpt-4o-mini")
            provider.chat([LLMMessage.of("user", "Hi")], temperature=0.2)

            call_kwargs = mock_client.chat.completions.create.call_args.kwargs
            assert call_kwargs["temperature"] == 0.2


# ---------------------------------------------------------------------------
# TestStubProviders
# ---------------------------------------------------------------------------

class TestStubProviders:
    def test_anthropic_raises_not_implemented_error_on_chat(self):
        from llm.anthropic_provider import AnthropicProvider
        p = AnthropicProvider(api_key="ant-test", model="claude-3-5-sonnet-20241022")
        with pytest.raises(NotImplementedError, match="not yet implemented"):
            p.chat([LLMMessage.of("user", "Hello")])

    def test_anthropic_provider_name(self):
        from llm.anthropic_provider import AnthropicProvider
        assert AnthropicProvider.PROVIDER_NAME == "anthropic"

    def test_anthropic_empty_key_raises(self):
        from llm.anthropic_provider import AnthropicProvider
        with pytest.raises(ValueError, match="API key"):
            AnthropicProvider(api_key="", model="claude-3-5-sonnet-20241022")

    def test_groq_provider_name(self):
        from llm.groq_provider import GroqProvider
        assert GroqProvider.PROVIDER_NAME == "groq"

    def test_groq_empty_key_raises(self):
        from llm.groq_provider import GroqProvider
        with pytest.raises(ValueError, match="API key"):
            GroqProvider(api_key="", model="llama-3.3-70b-versatile")

    def test_groq_constructs_with_valid_key(self):
        from llm.groq_provider import GroqProvider
        with patch("llm.groq_provider.OpenAI") as mock_openai:
            mock_openai.return_value = MagicMock()
            provider = GroqProvider(api_key="gsk-test", model="llama-3.3-70b-versatile")
            assert provider is not None
            call_kwargs = mock_openai.call_args.kwargs
            assert "groq.com" in call_kwargs.get("base_url", "")


# ---------------------------------------------------------------------------
# TestGeminiProvider
# ---------------------------------------------------------------------------

class TestGeminiProvider:
    def test_gemini_empty_key_raises(self):
        from llm.gemini_provider import GeminiProvider
        with pytest.raises(ValueError, match="API key"):
            GeminiProvider(api_key="", model="gemini-2.5-flash")

    def test_gemini_provider_name(self):
        from llm.gemini_provider import GeminiProvider
        assert GeminiProvider.PROVIDER_NAME == "gemini"

    def test_gemini_constructs_with_valid_key(self):
        from llm.gemini_provider import GeminiProvider
        with patch("llm.gemini_provider.OpenAI") as mock_openai:
            mock_openai.return_value = MagicMock()
            provider = GeminiProvider(api_key="gem-test", model="gemini-2.5-flash")
            assert provider is not None
            call_kwargs = mock_openai.call_args.kwargs
            assert "googleapis.com" in call_kwargs.get("base_url", "")

    def test_gemini_chat_passes_parameters(self):
        from llm.gemini_provider import GeminiProvider
        mock_completion = MagicMock()
        mock_completion.choices[0].message.content = "Gemini response"
        mock_completion.model = "gemini-2.5-flash"
        mock_completion.usage.prompt_tokens = 15
        mock_completion.usage.completion_tokens = 25
        mock_completion.usage.total_tokens = 40

        with patch("llm.gemini_provider.OpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_completion
            mock_openai_cls.return_value = mock_client

            provider = GeminiProvider(api_key="gem-test", model="gemini-2.5-flash")
            messages = [LLMMessage.of("user", "Hello Gemini")]
            result = provider.chat(messages, temperature=0.5)

            assert isinstance(result, LLMResponse)
            assert result.content == "Gemini response"
            assert result.provider == "gemini"
            assert result.usage["total_tokens"] == 40

            call_kwargs = mock_client.chat.completions.create.call_args.kwargs
            assert call_kwargs["model"] == "gemini-2.5-flash"
            assert call_kwargs["messages"] == messages
            assert call_kwargs["temperature"] == 0.5

    def test_gemini_json_mode_sets_response_format(self):
        from llm.gemini_provider import GeminiProvider
        mock_completion = MagicMock()
        mock_completion.choices[0].message.content = '{"reply": "test"}'
        mock_completion.model = "gemini-2.5-flash"
        mock_completion.usage = None

        with patch("llm.gemini_provider.OpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_completion
            mock_openai_cls.return_value = mock_client

            provider = GeminiProvider(api_key="gem-test", model="gemini-2.5-flash")
            provider.chat([{"role": "user", "content": "JSON"}], json_mode=True)

            call_kwargs = mock_client.chat.completions.create.call_args.kwargs
            assert call_kwargs["response_format"] == {"type": "json_object"}

