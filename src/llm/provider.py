"""LLM провайдер с поддержкой fallback и retry."""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING, Any, cast

from langchain.chat_models import init_chat_model
from langchain_core.language_models import SimpleChatModel
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.core.logging import get_logger
from src.llm.config import LLMConfig, get_llm_config
from src.llm.exceptions import (
    LLMAuthError,
    LLMContextLengthError,
    LLMError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMUnavailableError,
)

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

logger = get_logger(__name__)


class MockChatModel(SimpleChatModel):
    """
    Mock LLM для тестирования без реального API.

    Использует SimpleChatModel из langchain для совместимости с ReAct agent.
    """

    @property
    def _llm_type(self) -> str:
        """Тип LLM для логирования."""
        return "mock"

    def bind_tools(self, tools: Any, **kwargs: Any) -> Any:
        """
        Привязка tools для совместимости с ReAct agent.

        Mock не использует реальные tools, просто возвращаем self.
        """
        _ = tools, kwargs
        return self

    def _call(
        self,
        messages: list[Any],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> str:
        """Синхронная генерация."""
        _ = messages, stop, run_manager, kwargs
        return "Это mock-ответ. Для полноценной работы установите API ключ в переменную окружения."


class LLMProvider:
    """
    Провайдер LLM с поддержкой:
    - Lazy initialization модели
    - Автоматические retry с exponential backoff
    - Fallback на резервную модель
    - Mock режим при отсутствии API ключа
    - Параметры GPT-5.x (reasoning_effort, output_verbosity)
    """

    def __init__(self, config: LLMConfig | None = None) -> None:
        """
        Инициализация провайдера.

        Args:
            config: Конфигурация LLM. Если None, загружается из config/llm.yaml.
        """
        self._config = config or get_llm_config()
        self._model: BaseChatModel | MockChatModel | None = None

    @property
    def config(self) -> LLMConfig:
        """Текущая конфигурация."""
        return self._config

    @property
    def model(self) -> BaseChatModel | MockChatModel:
        """
        Lazy-initialized модель.

        Returns:
            BaseChatModel или MockChatModel в зависимости от конфигурации.
        """
        if self._model is None:
            self._model = self._create_model()
        return self._model

    def _create_model(self) -> BaseChatModel | MockChatModel:
        """Создать экземпляр модели."""
        if self._config.is_mock_mode:
            logger.warning(
                "No API key found, using mock LLM",
                extra={"provider": self._config.provider},
            )
            return MockChatModel()  # SimpleChatModel не принимает аргументы

        try:
            # Получаем параметры в зависимости от версии модели
            model_params = self._config.get_model_params()

            # Создаём базовые параметры для init_chat_model
            init_params: dict[str, Any] = {
                "model": self._config.model,
                "timeout": self._config.timeout,
                "max_retries": 0,  # Управляем retry на уровне провайдера
            }

            # Для GPT-5.x параметры идут через model_kwargs
            if self._config.is_gpt5:
                init_params["model_kwargs"] = model_params
            else:
                # Для старых моделей (GPT-4, etc) — напрямую
                init_params.update(model_params)

            model: BaseChatModel = cast(
                "BaseChatModel",
                init_chat_model(**init_params),
            )

            # Добавляем fallback если указан
            if self._config.fallback_model:
                fallback_params = init_params.copy()
                fallback_params["model"] = self._config.fallback_model

                fallback = cast(
                    "BaseChatModel",
                    init_chat_model(**fallback_params),
                )
                # with_fallbacks возвращает RunnableWithFallbacks, совместим с BaseChatModel
                model_with_fallback = cast("BaseChatModel", model.with_fallbacks([fallback]))
                logger.info(
                    "LLM initialized with fallback",
                    extra={
                        "primary": self._config.model,
                        "fallback": self._config.fallback_model,
                        "params": model_params,
                    },
                )
                return model_with_fallback

            logger.info(
                "LLM initialized",
                extra={
                    "model": self._config.model,
                    "params": model_params,
                },
            )

            return model

        except Exception as e:
            logger.error(
                "Failed to initialize LLM, falling back to mock",
                extra={"error": str(e), "model": self._config.model},
            )
            return MockChatModel()  # SimpleChatModel не принимает аргументы

    async def ainvoke_with_retry(
        self,
        messages: list[Any],
        **kwargs: Any,
    ) -> Any:
        """
        Вызов модели с автоматическим retry.

        Args:
            messages: Список сообщений
            **kwargs: Дополнительные параметры

        Returns:
            Ответ модели

        Raises:
            LLMError: При исчерпании попыток
        """
        retry_delays = self._config.retry_delays
        min_delay = retry_delays[0] if retry_delays else 1.0
        max_delay = retry_delays[-1] if retry_delays else 4.0

        retrying = AsyncRetrying(
            stop=stop_after_attempt(self._config.max_retries),
            wait=wait_exponential(multiplier=1, min=min_delay, max=max_delay),
            retry=retry_if_exception_type((TimeoutError, ConnectionError)),
            reraise=True,
        )

        try:
            async for attempt in retrying:
                with attempt:
                    try:
                        return await self.model.ainvoke(messages, **kwargs)
                    except TimeoutError as e:
                        logger.warning(
                            "LLM timeout, retrying",
                            extra={"attempt": attempt.retry_state.attempt_number},
                        )
                        raise LLMTimeoutError() from e
                    except Exception as e:
                        error = self._classify_error(e)
                        if isinstance(error, (LLMAuthError, LLMContextLengthError)):
                            # Не ретраим ошибки аутентификации и контекста
                            raise error from e
                        raise

        except LLMError:
            raise
        except Exception as e:
            raise LLMUnavailableError(str(e)) from e

        # Этот код не должен выполняться, но для type checker
        raise LLMUnavailableError("Unexpected error")

    def _classify_error(self, error: Exception) -> LLMError:
        """Классифицировать ошибку LLM."""
        error_str = str(error).lower()

        if "authentication" in error_str or "api key" in error_str:
            return LLMAuthError()
        if "rate limit" in error_str or "429" in error_str:
            return LLMRateLimitError()
        if "timeout" in error_str:
            return LLMTimeoutError()
        if "context length" in error_str or "too long" in error_str:
            return LLMContextLengthError()

        return LLMUnavailableError(str(error))


@lru_cache
def get_llm_provider() -> LLMProvider:
    """
    Получить singleton экземпляр LLM провайдера.

    Returns:
        LLMProvider instance
    """
    return LLMProvider()


def clear_llm_provider_cache() -> None:
    """Очистить кэш провайдера (для тестов)."""
    get_llm_provider.cache_clear()
