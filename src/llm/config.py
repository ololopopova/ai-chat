"""Конфигурация LLM провайдера с загрузкой из YAML."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml

# Путь к конфигу по умолчанию
DEFAULT_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "llm.yaml"

# Типы для параметров GPT-5.x
ReasoningEffort = Literal["none", "low", "medium", "high", "xhigh"]
OutputVerbosity = Literal["low", "medium", "high"]


@dataclass(frozen=True, slots=True)
class GenerationParams:
    """
    Параметры генерации для GPT-5.x.

    GPT-5.x не поддерживает temperature, вместо этого используются:
    - reasoning_effort: уровень усилий на рассуждение
    - output_verbosity: детализация ответа
    """

    reasoning_effort: ReasoningEffort = "low"
    output_verbosity: OutputVerbosity = "low"

    def to_api_params(self) -> dict[str, Any]:
        """Преобразовать в параметры API OpenAI."""
        return {
            "reasoning": {"effort": self.reasoning_effort},
            "text": {"verbosity": self.output_verbosity},
        }


@dataclass(frozen=True, slots=True)
class LLMConfig:
    """
    Конфигурация LLM провайдера.

    Загружается из config/llm.yaml. Секреты (API ключи) берутся из env vars.

    Attributes:
        model: Полный идентификатор модели (provider:model_name)
        fallback_model: Резервная модель при ошибках
        generation: Параметры генерации (reasoning_effort, output_verbosity)
        timeout: Таймаут запроса в секундах
        max_retries: Максимальное количество повторных попыток
        retry_delays: Задержки между retry (exponential backoff)
        api_key: API ключ (если не указан, берётся из env)
    """

    model: str = "openai:gpt-5.2"
    fallback_model: str | None = "openai:gpt-5-mini"
    generation: GenerationParams = field(default_factory=GenerationParams)
    timeout: int = 60
    max_retries: int = 3
    retry_delays: tuple[float, ...] = (1.0, 2.0, 4.0)
    api_key: str | None = None

    @property
    def provider(self) -> str:
        """Извлечь имя провайдера из model string."""
        if ":" in self.model:
            return self.model.split(":")[0]
        return "openai"

    @property
    def model_name(self) -> str:
        """Извлечь имя модели из model string."""
        if ":" in self.model:
            return self.model.split(":", 1)[1]
        return self.model

    @property
    def is_gpt5(self) -> bool:
        """Проверить, является ли модель GPT-5.x."""
        return "gpt-5" in self.model_name.lower()

    @property
    def is_mock_mode(self) -> bool:
        """Проверить, нужно ли использовать mock режим (нет API ключа)."""
        if os.getenv("USE_MOCK_LLM", "").lower() == "true":
            return True

        if self.api_key:
            return False

        # Проверяем env переменные для известных провайдеров
        provider_env_vars = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "google": "GOOGLE_API_KEY",
            "azure": "AZURE_OPENAI_API_KEY",
        }

        env_var = provider_env_vars.get(self.provider, f"{self.provider.upper()}_API_KEY")
        return not os.getenv(env_var)

    def get_model_params(self) -> dict[str, Any]:
        """
        Получить параметры для инициализации модели.

        Для GPT-5.x возвращает reasoning/text параметры.
        Для старых моделей — temperature.
        """
        if self.is_gpt5:
            return self.generation.to_api_params()
        # Fallback для старых моделей (GPT-4, etc)
        return {"temperature": 0.7}

    @classmethod
    def from_yaml(cls, config_path: Path | None = None) -> LLMConfig:
        """
        Загрузить конфигурацию из YAML файла.

        Args:
            config_path: Путь к файлу. Если None, используется default.

        Returns:
            LLMConfig instance
        """
        if config_path is None:
            config_path = DEFAULT_CONFIG_PATH

        if not config_path.exists():
            # Если файл не найден — возвращаем defaults
            return cls()

        with config_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        models = data.get("models", {})
        generation = data.get("generation", {})
        infrastructure = data.get("infrastructure", {})

        return cls(
            model=models.get("default", "openai:gpt-5.2"),
            fallback_model=models.get("fallback"),
            generation=GenerationParams(
                reasoning_effort=generation.get("reasoning_effort", "low"),
                output_verbosity=generation.get("output_verbosity", "low"),
            ),
            timeout=infrastructure.get("timeout", 60),
            max_retries=infrastructure.get("max_retries", 3),
            retry_delays=tuple(infrastructure.get("retry_delays", [1.0, 2.0, 4.0])),
        )

    def with_overrides(self, **kwargs: Any) -> LLMConfig:
        """Создать новую конфигурацию с переопределёнными параметрами."""
        generation = kwargs.get("generation", self.generation)
        if isinstance(generation, dict):
            generation = GenerationParams(**generation)

        return LLMConfig(
            model=kwargs.get("model", self.model),
            fallback_model=kwargs.get("fallback_model", self.fallback_model),
            generation=generation,
            timeout=kwargs.get("timeout", self.timeout),
            max_retries=kwargs.get("max_retries", self.max_retries),
            retry_delays=kwargs.get("retry_delays", self.retry_delays),
            api_key=kwargs.get("api_key", self.api_key),
        )


@lru_cache
def get_llm_config() -> LLMConfig:
    """
    Получить закэшированную конфигурацию LLM.

    Returns:
        LLMConfig из config/llm.yaml
    """
    return LLMConfig.from_yaml()


def clear_llm_config_cache() -> None:
    """Очистить кэш конфигурации (для тестов)."""
    get_llm_config.cache_clear()


# Для обратной совместимости
RETRY_DELAYS: tuple[float, ...] = (1.0, 2.0, 4.0)
