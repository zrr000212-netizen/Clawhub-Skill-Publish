import sys
import os
import time
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ai.llm_client import LLMClient, AIConfig, LLMError


class TestResolveApiKey:
    def test_plain_api_key(self):
        config = AIConfig(api_key="sk-plain-key")
        client = LLMClient(config)
        assert client.api_key == "sk-plain-key"

    def test_env_var_api_key(self):
        with patch.dict(os.environ, {"MY_API_KEY": "sk-from-env"}):
            config = AIConfig(api_key="${env:MY_API_KEY}")
            client = LLMClient(config)
            assert client.api_key == "sk-from-env"

    def test_env_var_not_set(self):
        with patch.dict(os.environ, {}, clear=False):
            env_key = "NONEXISTENT_KEY_12345"
            if env_key in os.environ:
                del os.environ[env_key]
            config = AIConfig(api_key="${env:NONEXISTENT_KEY_12345}")
            client = LLMClient(config)
            assert client.api_key == ""


class TestResolveApiBase:
    def test_openai_provider(self):
        config = AIConfig(provider="openai")
        client = LLMClient(config)
        assert client.api_base == "https://api.openai.com/v1"

    def test_azure_provider(self):
        config = AIConfig(provider="azure_openai")
        client = LLMClient(config)
        assert client.api_base == ""

    def test_custom_api_base(self):
        config = AIConfig(provider="custom", api_base="https://my-llm.example.com/v1/")
        client = LLMClient(config)
        assert client.api_base == "https://my-llm.example.com/v1"

    def test_custom_api_base_no_trailing_slash(self):
        config = AIConfig(provider="custom", api_base="https://my-llm.example.com/v1")
        client = LLMClient(config)
        assert client.api_base == "https://my-llm.example.com/v1"


class TestChatCompletion:
    def test_success(self):
        config = AIConfig(api_key="test-key", model="gpt-4", max_retries=0)
        client = LLMClient(config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "feat: new feature"}}]
        }

        with patch('requests.post', return_value=mock_response):
            result = client.chat_completion([{"role": "user", "content": "test"}])
            assert result["choices"][0]["message"]["content"] == "feat: new feature"

    def test_permanent_error_401(self):
        config = AIConfig(api_key="bad-key", max_retries=0)
        client = LLMClient(config)

        mock_response = MagicMock()
        mock_response.status_code = 401

        with patch('requests.post', return_value=mock_response):
            with pytest.raises(LLMError) as exc_info:
                client.chat_completion([{"role": "user", "content": "test"}])
            assert exc_info.value.error_type == "permanent"
            assert not exc_info.value.retryable

    def test_permanent_error_403(self):
        config = AIConfig(api_key="test", max_retries=0)
        client = LLMClient(config)

        mock_response = MagicMock()
        mock_response.status_code = 403

        with patch('requests.post', return_value=mock_response):
            with pytest.raises(LLMError) as exc_info:
                client.chat_completion([{"role": "user", "content": "test"}])
            assert exc_info.value.error_type == "permanent"

    def test_permanent_error_404(self):
        config = AIConfig(api_key="test", max_retries=0)
        client = LLMClient(config)

        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch('requests.post', return_value=mock_response):
            with pytest.raises(LLMError) as exc_info:
                client.chat_completion([{"role": "user", "content": "test"}])
            assert exc_info.value.error_type == "permanent"

    def test_transient_error_500(self):
        config = AIConfig(api_key="test", max_retries=0)
        client = LLMClient(config)

        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch('requests.post', return_value=mock_response):
            with pytest.raises(LLMError) as exc_info:
                client.chat_completion([{"role": "user", "content": "test"}])
            assert exc_info.value.error_type == "transient"
            assert exc_info.value.retryable

    def test_timeout_error(self):
        import requests as req
        config = AIConfig(api_key="test", max_retries=0)
        client = LLMClient(config)

        with patch('requests.post', side_effect=req.exceptions.Timeout()):
            with pytest.raises(LLMError) as exc_info:
                client.chat_completion([{"role": "user", "content": "test"}])
            assert exc_info.value.error_type == "transient"


class TestCircuitBreaker:
    def test_circuit_breaker_triggers(self):
        config = AIConfig(api_key="test", max_retries=0)
        client = LLMClient(config)
        client._circuit_breaker_threshold = 2

        mock_response = MagicMock()
        mock_response.status_code = 401

        with patch('requests.post', return_value=mock_response):
            with pytest.raises(LLMError):
                client.chat_completion([{"role": "user", "content": "test"}])
            with pytest.raises(LLMError):
                client.chat_completion([{"role": "user", "content": "test"}])

        assert client._circuit_breaker_failures >= 2
        assert client._is_circuit_breaker_open()

    def test_circuit_breaker_blocks_calls(self):
        config = AIConfig(api_key="test", max_retries=0)
        client = LLMClient(config)
        client._circuit_breaker_failures = 3
        client._circuit_breaker_last_failure_time = time.time()

        with pytest.raises(LLMError) as exc_info:
            client.chat_completion([{"role": "user", "content": "test"}])
        assert "熔断器已开启" in exc_info.value.message

    def test_circuit_breaker_resets_after_timeout(self):
        config = AIConfig(api_key="test", max_retries=0)
        client = LLMClient(config)
        client._circuit_breaker_failures = 3
        client._circuit_breaker_last_failure_time = time.time() - 301

        assert not client._is_circuit_breaker_open()
        assert client._circuit_breaker_failures == 0