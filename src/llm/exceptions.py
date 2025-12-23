"""LLM-специфичные исключения."""

from src.core.exceptions import AppError


class LLMError(AppError):
    """Базовое исключение для LLM ошибок."""

    def __init__(self, message: str, code: str = "LLM_ERROR") -> None:
        super().__init__(message, code=code)


class LLMUnavailableError(LLMError):
    """LLM API недоступен."""

    def __init__(self, message: str = "LLM API is unavailable") -> None:
        super().__init__(message, code="LLM_UNAVAILABLE")


class LLMRateLimitError(LLMError):
    """Превышен лимит запросов к LLM."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: float | None = None,
    ) -> None:
        super().__init__(message, code="RATE_LIMIT")
        self.retry_after = retry_after


class LLMAuthError(LLMError):
    """Ошибка аутентификации LLM (неверный API ключ)."""

    def __init__(self, message: str = "Invalid API key") -> None:
        super().__init__(message, code="AUTH_ERROR")


class LLMTimeoutError(LLMError):
    """Таймаут при запросе к LLM."""

    def __init__(self, message: str = "LLM request timeout") -> None:
        super().__init__(message, code="TIMEOUT")


class LLMContextLengthError(LLMError):
    """Превышена максимальная длина контекста."""

    def __init__(self, message: str = "Context length exceeded") -> None:
        super().__init__(message, code="CONTEXT_LENGTH_ERROR")


class LLMInvalidResponseError(LLMError):
    """LLM вернул невалидный ответ."""

    def __init__(self, message: str = "Invalid LLM response") -> None:
        super().__init__(message, code="INVALID_RESPONSE")
