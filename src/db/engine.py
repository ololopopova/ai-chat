"""Async SQLAlchemy Engine Factory.

Создаёт и управляет async engine для PostgreSQL с connection pooling.
"""

import logging
from functools import lru_cache
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

if TYPE_CHECKING:
    from src.core.config import Settings

logger = logging.getLogger(__name__)


def create_engine_from_settings(settings: "Settings") -> AsyncEngine:
    """
    Создать async engine из настроек приложения.

    Args:
        settings: Настройки приложения с параметрами подключения к БД.

    Returns:
        Настроенный AsyncEngine с connection pool.

    Note:
        Pool настройки:
        - pool_size: базовый размер пула соединений
        - max_overflow: дополнительные соединения сверх pool_size
        - pool_timeout: таймаут ожидания соединения из пула
        - pool_recycle: время жизни соединения (для избежания stale connections)
        - pool_pre_ping: проверка соединения перед использованием
    """
    engine = create_async_engine(
        settings.database_url,
        echo=settings.database_echo,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_timeout=settings.database_pool_timeout,
        pool_recycle=settings.database_pool_recycle,
        pool_pre_ping=True,  # Проверяем соединение перед использованием
    )

    logger.info(
        "Database engine created",
        extra={
            "pool_size": settings.database_pool_size,
            "max_overflow": settings.database_max_overflow,
            "echo": settings.database_echo,
        },
    )

    return engine


@lru_cache
def get_engine() -> AsyncEngine:
    """
    Получить закэшированный async engine.

    Использует настройки по умолчанию из get_settings().
    Кэширует engine для переиспользования во всём приложении.

    Returns:
        Singleton AsyncEngine instance.
    """
    from src.core.config import get_settings

    return create_engine_from_settings(get_settings())


def clear_engine_cache() -> None:
    """Очистить кэш engine (для тестов)."""
    get_engine.cache_clear()


async def check_database_connection(
    engine: AsyncEngine,
    timeout_seconds: float = 5.0,
) -> bool:
    """
    Проверить подключение к базе данных.

    Args:
        engine: AsyncEngine для проверки.
        timeout_seconds: Таймаут проверки в секундах.

    Returns:
        True если подключение успешно, False иначе.
    """
    import asyncio

    from sqlalchemy import text

    try:
        async with asyncio.timeout(timeout_seconds):
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
                return True
    except Exception as e:
        logger.warning("Database connection check failed", extra={"error": str(e)})
        return False


async def dispose_engine(engine: AsyncEngine) -> None:
    """
    Корректно закрыть engine и все соединения.

    Args:
        engine: AsyncEngine для закрытия.
    """
    await engine.dispose()
    logger.info("Database engine disposed")
