"""Конфигурация приложения через Pydantic Settings."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Корень проекта
PROJECT_ROOT = Path(__file__).parent.parent.parent


class Settings(BaseSettings):
    """Настройки приложения, загружаемые из переменных окружения."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Версия приложения
    app_version: str = "0.1.0"

    # Окружение
    app_env: Literal["development", "staging", "production"] = "development"
    app_debug: bool = False

    # API Server настройки
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 1
    api_reload: bool = True

    # API URLs (для клиентов)
    api_base_url: str = "http://localhost:8000"
    api_ws_url: str = "ws://localhost:8000"

    # CORS настройки
    cors_origins: list[str] = Field(default=["http://localhost:8501", "http://127.0.0.1:8501"])

    # WebSocket настройки
    ws_heartbeat_interval: int = 30  # секунды
    ws_message_max_size: int = 65536  # 64KB
    ws_connection_timeout: int = 300  # 5 минут

    # UI настройки
    ui_title: str = "AI Ассистент"
    ui_page_icon: str = "🤖"

    # Mock режим
    use_mock_api: bool = True

    # Пути к файлам конфигурации
    domains_config_path: Path = Field(default=PROJECT_ROOT / "config" / "domains.yaml")

    @property
    def is_development(self) -> bool:
        """Проверка, что приложение в режиме разработки."""
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        """Проверка, что приложение в production режиме."""
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Получить закэшированный экземпляр настроек."""
    return Settings()


def clear_settings_cache() -> None:
    """Очистить кэш настроек (для тестов)."""
    get_settings.cache_clear()
