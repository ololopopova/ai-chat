"""Настройка логирования приложения."""

import logging
import sys
from functools import lru_cache

from src.core.config import get_settings


@lru_cache
def get_logger(name: str = "ai_chat") -> logging.Logger:
    """
    Получить настроенный логгер.

    Args:
        name: Имя логгера

    Returns:
        Настроенный экземпляр логгера
    """
    settings = get_settings()

    logger = logging.getLogger(name)

    # Устанавливаем уровень в зависимости от окружения
    if settings.app_debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    # Проверяем, есть ли уже handler
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)

        logger.addHandler(handler)

    return logger
