"""
Профессиональная система логирования.

Features:
- Structured JSON logging для production (ELK-ready)
- Human-readable формат для development
- Автоматический thread_id и request_id в каждом сообщении
- Ротация логов по размеру
- Разные уровни для консоли и файла
"""

from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from src.core.config import get_settings

if TYPE_CHECKING:
    from collections.abc import MutableMapping

# Context variables для thread_id и request_id
_thread_id_var: ContextVar[str | None] = ContextVar("thread_id", default=None)
_request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


def set_thread_id(thread_id: str) -> None:
    """Установить thread_id для текущего контекста."""
    _thread_id_var.set(thread_id)


def get_thread_id() -> str | None:
    """Получить thread_id из текущего контекста."""
    return _thread_id_var.get()


def set_request_id(request_id: str) -> None:
    """Установить request_id для текущего контекста."""
    _request_id_var.set(request_id)


def get_request_id() -> str | None:
    """Получить request_id из текущего контекста."""
    return _request_id_var.get()


class ContextFilter(logging.Filter):
    """Фильтр для добавления thread_id и request_id в записи лога."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Добавить контекстные переменные в запись."""
        record.thread_id = get_thread_id() or "-"
        record.request_id = get_request_id() or "-"
        return True


class JSONFormatter(logging.Formatter):
    """
    JSON formatter для structured logging.

    Формат подходит для ELK, Datadog, CloudWatch и других систем.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Форматировать запись в JSON."""
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "thread_id": getattr(record, "thread_id", None),
            "request_id": getattr(record, "request_id", None),
        }

        # Добавляем extra поля
        if hasattr(record, "extra") and record.extra:
            log_data["extra"] = record.extra

        # Стандартные extra поля из record.__dict__
        standard_keys = {
            "name",
            "msg",
            "args",
            "created",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "module",
            "msecs",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "stack_info",
            "exc_info",
            "exc_text",
            "thread",
            "threadName",
            "taskName",
            "thread_id",
            "request_id",
            "message",
            "extra",
        }

        for key, value in record.__dict__.items():
            if key not in standard_keys and not key.startswith("_"):
                if "extra" not in log_data:
                    log_data["extra"] = {}
                log_data["extra"][key] = value

        # Добавляем информацию об исключении
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Добавляем location для DEBUG
        if record.levelno <= logging.DEBUG:
            log_data["location"] = {
                "file": record.filename,
                "line": record.lineno,
                "function": record.funcName,
            }

        return json.dumps(log_data, ensure_ascii=False, default=str)


class HumanReadableFormatter(logging.Formatter):
    """
    Human-readable formatter для development.

    Включает цветовую подсветку уровней и контекст.
    """

    # ANSI цвета
    COLORS: ClassVar[dict[str, str]] = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET: ClassVar[str] = "\033[0m"

    def __init__(self, use_colors: bool = True) -> None:
        """Инициализация formatter."""
        super().__init__()
        self.use_colors = use_colors

    def format(self, record: logging.LogRecord) -> str:
        """Форматировать запись в человекочитаемый формат."""
        # Время
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Уровень с цветом
        level = record.levelname
        if self.use_colors and level in self.COLORS:
            level = f"{self.COLORS[level]}{level:8}{self.RESET}"
        else:
            level = f"{level:8}"

        # Контекст
        thread_id = getattr(record, "thread_id", "-")
        request_id = getattr(record, "request_id", "-")

        # Базовое сообщение
        message = record.getMessage()

        # Формируем строку
        parts = [f"{timestamp} | {level} | {record.name}"]

        # Добавляем контекст если есть
        if thread_id != "-":
            parts.append(f"[thread:{thread_id[:8]}]")
        if request_id != "-":
            parts.append(f"[req:{request_id[:8]}]")

        parts.append(f"| {message}")

        # Extra поля
        extra_parts = []
        standard_keys = {
            "name",
            "msg",
            "args",
            "created",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "module",
            "msecs",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "stack_info",
            "exc_info",
            "exc_text",
            "thread",
            "threadName",
            "taskName",
            "thread_id",
            "request_id",
            "message",
        }

        for key, value in record.__dict__.items():
            if key not in standard_keys and not key.startswith("_"):
                extra_parts.append(f"{key}={value}")

        if extra_parts:
            parts.append(f"| {', '.join(extra_parts)}")

        result = " ".join(parts)

        # Исключение
        if record.exc_info:
            result += "\n" + self.formatException(record.exc_info)

        return result


class LoggerAdapter(logging.LoggerAdapter[logging.Logger]):
    """
    Adapter для добавления extra полей к логам.

    Пример:
        logger = get_logger(__name__)
        logger.info("Message", extra={"user_id": 123})
    """

    def process(
        self, msg: str, kwargs: MutableMapping[str, Any]
    ) -> tuple[str, MutableMapping[str, Any]]:
        """Обработать сообщение и kwargs."""
        # Объединяем extra из adapter и из вызова
        extra = {**self.extra} if self.extra else {}
        if "extra" in kwargs:
            extra.update(kwargs["extra"])
        kwargs["extra"] = extra
        return msg, kwargs


def setup_logging() -> None:
    """
    Настроить систему логирования.

    Вызывается один раз при старте приложения.
    """
    settings = get_settings()

    # Корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if settings.app_debug else logging.INFO)

    # Очищаем существующие handlers
    root_logger.handlers.clear()

    # Context filter для всех handlers
    context_filter = ContextFilter()

    # === Console Handler ===
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if settings.app_debug else logging.INFO)
    console_handler.addFilter(context_filter)

    # Формат зависит от окружения
    if settings.is_development:
        console_handler.setFormatter(HumanReadableFormatter(use_colors=True))
    else:
        console_handler.setFormatter(JSONFormatter())

    root_logger.addHandler(console_handler)

    # === File Handler (production или если включен debug) ===
    if not settings.is_development or settings.app_debug:
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)

        # Основной лог файл с ротацией
        file_handler = RotatingFileHandler(
            logs_dir / "app.log",
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.INFO)
        file_handler.addFilter(context_filter)
        file_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(file_handler)

        # Отдельный файл для ошибок
        error_handler = RotatingFileHandler(
            logs_dir / "error.log",
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding="utf-8",
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.addFilter(context_filter)
        error_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(error_handler)

    # Уменьшаем шум от библиотек
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> LoggerAdapter:
    """
    Получить логгер для модуля.

    Args:
        name: Имя модуля (обычно __name__)

    Returns:
        LoggerAdapter с поддержкой extra полей

    Example:
        logger = get_logger(__name__)
        logger.info("User logged in", extra={"user_id": 123})
    """
    # Настраиваем логирование при первом вызове
    if not logging.getLogger().handlers:
        setup_logging()

    return LoggerAdapter(logging.getLogger(name), {})


# Для обратной совместимости — автоматическая настройка при импорте
# (опционально, можно убрать если хотите явный вызов setup_logging())
