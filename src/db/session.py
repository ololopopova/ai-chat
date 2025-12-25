"""AsyncSession Factory.

Создаёт и управляет async sessions для работы с БД.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)


class AsyncSessionFactory:
    """
    Фабрика для создания async sessions.

    Инкапсулирует sessionmaker и предоставляет методы
    для получения сессий как context managers.
    """

    def __init__(self, engine: "AsyncEngine") -> None:
        """
        Инициализировать фабрику сессий.

        Args:
            engine: AsyncEngine для создания сессий.
        """
        self._engine = engine
        self._session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,  # Не инвалидируем объекты после commit
            autoflush=False,  # Явный flush для контроля
            autocommit=False,  # Явные транзакции
        )

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession]:
        """
        Получить сессию как async context manager.

        Автоматически закрывает сессию при выходе из контекста.
        При ошибке выполняет rollback.

        Yields:
            AsyncSession для работы с БД.

        Example:
            async with factory.get_session() as session:
                result = await session.execute(query)
        """
        session = self._session_factory()
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    @asynccontextmanager
    async def get_transaction(self) -> AsyncGenerator[AsyncSession]:
        """
        Получить сессию с автоматическим commit/rollback.

        Commits при успешном выходе, rollback при исключении.

        Yields:
            AsyncSession с транзакцией.

        Example:
            async with factory.get_transaction() as session:
                session.add(model)
                # auto-commit on exit
        """
        async with self.get_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    @property
    def engine(self) -> "AsyncEngine":
        """Получить engine фабрики."""
        return self._engine


# Глобальная фабрика сессий (инициализируется лениво)
_session_factory: AsyncSessionFactory | None = None


def get_session_factory() -> AsyncSessionFactory:
    """
    Получить глобальную фабрику сессий.

    Создаёт фабрику при первом вызове.

    Returns:
        AsyncSessionFactory singleton.
    """
    global _session_factory
    if _session_factory is None:
        from src.db.engine import get_engine

        _session_factory = AsyncSessionFactory(get_engine())
    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession]:
    """
    Dependency для FastAPI — получить async session.

    Использует глобальную фабрику сессий.

    Yields:
        AsyncSession для использования в endpoint.

    Example:
        @router.get("/items")
        async def get_items(session: AsyncSession = Depends(get_session)):
            ...
    """
    factory = get_session_factory()
    async with factory.get_session() as session:
        yield session


def reset_session_factory() -> None:
    """Сбросить глобальную фабрику сессий (для тестов)."""
    global _session_factory
    _session_factory = None
