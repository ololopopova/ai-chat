"""Конфигурация приложения через Pydantic Settings."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, computed_field
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

    # ==========================================
    # Database Settings (PostgreSQL + asyncpg)
    # ==========================================
    database_url: str = Field(
        default="postgresql+asyncpg://ai_chat:ai_chat_secret@localhost:5433/ai_chat",
        description="Async PostgreSQL connection URL",
    )
    database_pool_size: int = Field(default=5, ge=1, le=50, description="Connection pool size")
    database_max_overflow: int = Field(
        default=10, ge=0, le=100, description="Max overflow connections"
    )
    database_pool_timeout: int = Field(
        default=30, ge=5, le=120, description="Pool connection timeout in seconds"
    )
    database_pool_recycle: int = Field(
        default=1800, ge=300, description="Connection recycle time in seconds"
    )
    database_echo: bool = Field(default=False, description="Echo SQL queries to log")

    # ==========================================
    # Redis Settings
    # ==========================================
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )
    redis_max_connections: int = Field(default=10, ge=1, le=100)
    redis_socket_timeout: float = Field(default=5.0, ge=1.0, le=30.0)
    redis_socket_connect_timeout: float = Field(default=5.0, ge=1.0, le=30.0)

    @property
    def is_development(self) -> bool:
        """Проверка, что приложение в режиме разработки."""
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        """Проверка, что приложение в production режиме."""
        return self.app_env == "production"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url_sync(self) -> str:
        """Синхронный URL для Alembic (заменяем asyncpg на psycopg2)."""
        return self.database_url.replace("+asyncpg", "")


@lru_cache
def get_settings() -> Settings:
    """Получить закэшированный экземпляр настроек."""
    return Settings()


def clear_settings_cache() -> None:
    """Очистить кэш настроек (для тестов)."""
    get_settings.cache_clear()
