"""Конфигурация приложения через Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения, загружаемые из переменных окружения."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Окружение
    app_env: Literal["development", "staging", "production"] = "development"
    app_debug: bool = False

    # API URLs
    api_base_url: str = "http://localhost:8000"
    api_ws_url: str = "ws://localhost:8000"

    # UI настройки
    ui_title: str = "AI Ассистент"
    ui_page_icon: str = "🤖"

    # Mock режим
    use_mock_api: bool = True

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
