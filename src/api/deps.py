"""Dependency injection для FastAPI."""

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from src.core.config import Settings, get_settings


def get_app_settings() -> Settings:
    """
    Получить настройки приложения.

    Dependency для инъекции в route handlers.
    """
    return get_settings()


@lru_cache
def load_domains_config(config_path: Path | None = None) -> dict[str, Any]:
    """
    Загрузить конфигурацию доменов из YAML файла.

    Args:
        config_path: Путь к файлу конфигурации. Если None, используется из настроек.

    Returns:
        Словарь с конфигурацией доменов.

    Raises:
        FileNotFoundError: Если файл не найден.
        yaml.YAMLError: Если файл содержит невалидный YAML.
    """
    if config_path is None:
        config_path = get_settings().domains_config_path

    if not config_path.exists():
        raise FileNotFoundError(f"Domains config not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as f:
        config: dict[str, Any] = yaml.safe_load(f)

    return config


def get_domains_config() -> dict[str, Any]:
    """
    Dependency для получения конфигурации доменов.

    Returns:
        Словарь с конфигурацией доменов.
    """
    return load_domains_config()


def clear_domains_cache() -> None:
    """Очистить кэш конфигурации доменов (для тестов)."""
    load_domains_config.cache_clear()

