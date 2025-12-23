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


# ==========================================
# Repository Layer Exceptions
# ==========================================


class RepositoryError(AppError):
    """Базовое исключение для ошибок репозитория."""

    def __init__(self, message: str, entity: str | None = None) -> None:
        """
        Инициализация ошибки репозитория.

        Args:
            message: Текст ошибки.
            entity: Название сущности (Domain, Chunk и т.д.).
        """
        super().__init__(message, code="REPOSITORY_ERROR")
        self.entity = entity


class EntityNotFoundError(RepositoryError):
    """Сущность не найдена в базе данных."""

    def __init__(
        self,
        entity: str,
        identifier: str | None = None,
    ) -> None:
        """
        Инициализация ошибки "не найдено".

        Args:
            entity: Название сущности.
            identifier: Идентификатор (id, slug и т.д.).
        """
        if identifier:
            message = f"{entity} with identifier '{identifier}' not found"
        else:
            message = f"{entity} not found"
        super().__init__(message, entity=entity)
        self.code = "NOT_FOUND"
        self.identifier = identifier


class EntityAlreadyExistsError(RepositoryError):
    """Сущность уже существует (нарушение уникальности)."""

    def __init__(
        self,
        entity: str,
        field: str,
        value: str,
    ) -> None:
        """
        Инициализация ошибки дубликата.

        Args:
            entity: Название сущности.
            field: Поле с конфликтом.
            value: Значение, которое уже существует.
        """
        message = f"{entity} with {field}='{value}' already exists"
        super().__init__(message, entity=entity)
        self.code = "ALREADY_EXISTS"
        self.field = field
        self.value = value


class DatabaseConnectionError(RepositoryError):
    """Ошибка подключения к базе данных."""

    def __init__(self, message: str = "Database connection failed") -> None:
        """Инициализация ошибки подключения."""
        super().__init__(message)
        self.code = "DATABASE_CONNECTION_ERROR"


class TransactionError(RepositoryError):
    """Ошибка транзакции (commit/rollback)."""

    def __init__(self, message: str, operation: str = "unknown") -> None:
        """
        Инициализация ошибки транзакции.

        Args:
            message: Текст ошибки.
            operation: Операция (commit, rollback).
        """
        super().__init__(message)
        self.code = "TRANSACTION_ERROR"
        self.operation = operation
