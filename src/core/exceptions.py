"""Базовые исключения приложения."""


class AppError(Exception):
    """Базовое исключение приложения."""

    def __init__(self, message: str, code: str | None = None) -> None:
        """
        Инициализация исключения.

        Args:
            message: Текст ошибки
            code: Код ошибки для программной обработки
        """
        super().__init__(message)
        self.message = message
        self.code = code

    def __str__(self) -> str:
        """Строковое представление ошибки."""
        if self.code:
            return f"[{self.code}] {self.message}"
        return self.message


class ConfigError(AppError):
    """Ошибка конфигурации приложения."""

    def __init__(self, message: str) -> None:
        """Инициализация ошибки конфигурации."""
        super().__init__(message, code="CONFIG_ERROR")


class ValidationError(AppError):
    """Ошибка валидации данных."""

    def __init__(self, message: str, field: str | None = None) -> None:
        """
        Инициализация ошибки валидации.

        Args:
            message: Текст ошибки
            field: Имя поля с ошибкой
        """
        super().__init__(message, code="VALIDATION_ERROR")
        self.field = field

    def __str__(self) -> str:
        """Строковое представление ошибки."""
        if self.field:
            return f"[{self.code}] {self.field}: {self.message}"
        return f"[{self.code}] {self.message}"
