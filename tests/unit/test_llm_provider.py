"""Тесты для LLM провайдера."""

import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import patch

import pytest
import yaml

from src.llm.config import (
    GenerationParams,
    LLMConfig,
    clear_llm_config_cache,
)
from src.llm.exceptions import (
    LLMAuthError,
    LLMContextLengthError,
    LLMError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMUnavailableError,
)
from src.llm.provider import LLMProvider, MockChatModel, clear_llm_provider_cache


class TestGenerationParams:
    """Тесты для GenerationParams."""

    def test_default_params(self) -> None:
        """Проверка параметров по умолчанию."""
        params = GenerationParams()
        assert params.reasoning_effort == "low"
        assert params.output_verbosity == "low"

    def test_custom_params(self) -> None:
        """Проверка кастомных параметров."""
        params = GenerationParams(reasoning_effort="high", output_verbosity="medium")
        assert params.reasoning_effort == "high"
        assert params.output_verbosity == "medium"

    def test_to_api_params(self) -> None:
        """Проверка преобразования в API параметры."""
        params = GenerationParams(reasoning_effort="xhigh", output_verbosity="high")
        api_params = params.to_api_params()
        assert api_params == {
            "reasoning": {"effort": "xhigh"},
            "text": {"verbosity": "high"},
        }


class TestLLMConfig:
    """Тесты для LLMConfig."""

    def setup_method(self) -> None:
        """Очистка кэша перед каждым тестом."""
        clear_llm_config_cache()

    def test_default_config(self) -> None:
        """Проверка конфигурации по умолчанию."""
        config = LLMConfig()
        assert config.model == "openai:gpt-5.2"
        assert config.fallback_model == "openai:gpt-5-mini"
        assert config.timeout == 60
        assert config.max_retries == 3
        assert config.generation.reasoning_effort == "low"
        assert config.generation.output_verbosity == "low"

    def test_provider_extraction(self) -> None:
        """Проверка извлечения провайдера."""
        config = LLMConfig(model="openai:gpt-5.2")
        assert config.provider == "openai"
        assert config.model_name == "gpt-5.2"

    def test_provider_anthropic(self) -> None:
        """Проверка извлечения провайдера Anthropic."""
        config = LLMConfig(model="anthropic:claude-3-opus")
        assert config.provider == "anthropic"
        assert config.model_name == "claude-3-opus"

    def test_provider_without_colon(self) -> None:
        """Провайдер по умолчанию когда нет двоеточия."""
        config = LLMConfig(model="gpt-5.2")
        assert config.provider == "openai"
        assert config.model_name == "gpt-5.2"

    def test_is_gpt5_true(self) -> None:
        """Проверка определения GPT-5.x."""
        config = LLMConfig(model="openai:gpt-5.2")
        assert config.is_gpt5 is True

        config2 = LLMConfig(model="openai:gpt-5-mini")
        assert config2.is_gpt5 is True

    def test_is_mock_mode_no_key(self) -> None:
        """Mock режим при отсутствии ключа."""
        with patch.dict("os.environ", {}, clear=True):
            config = LLMConfig()
            # Без OPENAI_API_KEY должен быть mock mode
            assert config.is_mock_mode is True

    def test_is_mock_mode_with_key(self):
        """Проверка is_mock_mode если API ключ есть."""
        # Убедимся, что USE_MOCK_LLM не влияет (или явно сброшен)
        # Using string path for patch.dict to be safe
        with patch.dict(os.environ, {"USE_MOCK_LLM": ""}):
            config = LLMConfig(api_key="sk-test-key")
            assert config.is_mock_mode is False

    def test_get_model_params_gpt5(self) -> None:
        """Параметры для GPT-5.x."""
        config = LLMConfig(
            model="openai:gpt-5.2",
            generation=GenerationParams(reasoning_effort="high", output_verbosity="low"),
        )
        params = config.get_model_params()
        assert params == {
            "reasoning": {"effort": "high"},
            "text": {"verbosity": "low"},
        }

    def test_get_model_params_legacy(self) -> None:
        """Параметры для старых моделей (GPT-4)."""
        config = LLMConfig(model="openai:gpt-4o")
        params = config.get_model_params()
        assert params == {"temperature": 0.7}

    def test_with_overrides(self) -> None:
        """Проверка создания конфига с переопределениями."""
        config = LLMConfig(timeout=30)
        new_config = config.with_overrides(
            timeout=120,
            generation=GenerationParams(reasoning_effort="xhigh", output_verbosity="high"),
        )
        assert new_config.timeout == 120
        assert new_config.generation.reasoning_effort == "xhigh"
        assert new_config.max_retries == config.max_retries

    def test_from_yaml(self) -> None:
        """Загрузка конфига из YAML."""
        yaml_content = {
            "models": {
                "default": "openai:gpt-5.2",
                "fallback": "openai:gpt-5-mini",
            },
            "generation": {
                "reasoning_effort": "medium",
                "output_verbosity": "high",
            },
            "infrastructure": {
                "timeout": 90,
                "max_retries": 5,
                "retry_delays": [2.0, 4.0, 8.0],
            },
        }

        with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(yaml_content, f)
            config_path = Path(f.name)

        try:
            config = LLMConfig.from_yaml(config_path)
            assert config.model == "openai:gpt-5.2"
            assert config.fallback_model == "openai:gpt-5-mini"
            assert config.generation.reasoning_effort == "medium"
            assert config.generation.output_verbosity == "high"
            assert config.timeout == 90
            assert config.max_retries == 5
            assert config.retry_delays == (2.0, 4.0, 8.0)
        finally:
            config_path.unlink()

    def test_from_yaml_missing_file(self) -> None:
        """Defaults при отсутствии YAML файла."""
        config = LLMConfig.from_yaml(Path("/nonexistent/path.yaml"))
        assert config.model == "openai:gpt-5.2"
        assert config.generation.reasoning_effort == "low"


class TestRetryDelays:
    """Тесты для retry delays."""

    def test_retry_delays_values(self) -> None:
        """Проверка значений задержек."""
        config = LLMConfig()
        assert config.retry_delays == (1.0, 2.0, 4.0)

    def test_retry_delays_exponential(self) -> None:
        """Проверка экспоненциального роста."""
        config = LLMConfig()
        for i in range(len(config.retry_delays) - 1):
            assert config.retry_delays[i + 1] >= config.retry_delays[i]


class TestMockChatModel:
    """Тесты для MockChatModel."""

    @pytest.mark.asyncio
    async def test_mock_ainvoke(self) -> None:
        """Mock модель возвращает ответ."""
        model = MockChatModel()  # SimpleChatModel не принимает аргументы

        response = await model.ainvoke([{"role": "user", "content": "Hi"}])

        assert hasattr(response, "content")
        assert "mock" in response.content.lower() or "Mock" in response.content

    @pytest.mark.asyncio
    async def test_mock_astream(self) -> None:
        """Mock модель стримит токены."""
        model = MockChatModel()  # SimpleChatModel не принимает аргументы

        chunks = []
        async for chunk in model.astream([{"role": "user", "content": "Hi"}]):
            chunks.append(chunk.content)

        assert len(chunks) > 0
        full_response = "".join(chunks)
        assert len(full_response) > 0


class TestLLMProvider:
    """Тесты для LLMProvider."""

    def setup_method(self) -> None:
        """Очистка кэша перед каждым тестом."""
        clear_llm_provider_cache()
        clear_llm_config_cache()

    def test_provider_init_default(self) -> None:
        """Инициализация провайдера с дефолтным конфигом."""
        provider = LLMProvider()
        assert provider.config is not None
        assert provider.config.model == "openai:gpt-5.2"

    def test_provider_init_custom_config(self) -> None:
        """Инициализация провайдера с кастомным конфигом."""
        config = LLMConfig(
            model="anthropic:claude-3",
            generation=GenerationParams(reasoning_effort="high", output_verbosity="medium"),
        )
        provider = LLMProvider(config)
        assert provider.config.model == "anthropic:claude-3"
        assert provider.config.generation.reasoning_effort == "high"

    def test_provider_lazy_model(self) -> None:
        """Модель создаётся лениво."""
        with patch.dict("os.environ", {}, clear=True):
            provider = LLMProvider()
            assert provider._model is None
            model = provider.model  # Trigger creation
            assert provider._model is not None
            # Без API ключа должен быть MockChatModel
            assert isinstance(model, MockChatModel)

    def test_classify_error_auth(self) -> None:
        """Классификация ошибки аутентификации."""
        provider = LLMProvider()
        error = Exception("Invalid API key provided")
        result = provider._classify_error(error)
        assert isinstance(result, LLMAuthError)

    def test_classify_error_rate_limit(self) -> None:
        """Классификация rate limit ошибки."""
        provider = LLMProvider()
        error = Exception("Rate limit exceeded, 429")
        result = provider._classify_error(error)
        assert isinstance(result, LLMRateLimitError)

    def test_classify_error_timeout(self) -> None:
        """Классификация timeout ошибки."""
        provider = LLMProvider()
        error = Exception("Request timeout")
        result = provider._classify_error(error)
        assert isinstance(result, LLMTimeoutError)

    def test_classify_error_context(self) -> None:
        """Классификация context length ошибки."""
        provider = LLMProvider()
        error = Exception("Context length exceeded maximum")
        result = provider._classify_error(error)
        assert isinstance(result, LLMContextLengthError)

    def test_classify_error_unknown(self) -> None:
        """Классификация неизвестной ошибки."""
        provider = LLMProvider()
        error = Exception("Some unknown error")
        result = provider._classify_error(error)
        assert isinstance(result, LLMUnavailableError)


class TestLLMExceptions:
    """Тесты для LLM исключений."""

    def test_llm_error_base(self) -> None:
        """Базовое LLM исключение."""
        error = LLMError("Test error")
        assert error.message == "Test error"
        assert error.code == "LLM_ERROR"

    def test_llm_unavailable(self) -> None:
        """LLM недоступен."""
        error = LLMUnavailableError()
        assert error.code == "LLM_UNAVAILABLE"

    def test_llm_rate_limit(self) -> None:
        """Rate limit с retry_after."""
        error = LLMRateLimitError(retry_after=30.0)
        assert error.code == "RATE_LIMIT"
        assert error.retry_after == 30.0

    def test_llm_auth_error(self) -> None:
        """Auth ошибка."""
        error = LLMAuthError()
        assert error.code == "AUTH_ERROR"

    def test_llm_timeout(self) -> None:
        """Timeout ошибка."""
        error = LLMTimeoutError()
        assert error.code == "TIMEOUT"
