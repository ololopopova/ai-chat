"""AsyncPostgresSaver wrapper для персистентности состояния."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from src.core.config import get_settings
from src.core.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

logger = get_logger(__name__)


def _get_checkpointer_db_uri() -> str:
    """
    Получить URI для checkpointer.

    AsyncPostgresSaver использует psycopg3, который требует
    postgresql:// (без +asyncpg).
    """
    settings = get_settings()
    # Преобразуем asyncpg URL в psycopg URL
    db_url = settings.database_url
    db_url = db_url.replace("+asyncpg", "")
    return db_url


@asynccontextmanager
async def get_checkpointer() -> AsyncGenerator[AsyncPostgresSaver]:
    """
    Получить async checkpointer для LangGraph.

    Создаёт AsyncPostgresSaver из connection string и настраивает
    таблицы при первом запуске.

    Yields:
        AsyncPostgresSaver instance

    Example:
        async with get_checkpointer() as checkpointer:
            graph = builder.compile(checkpointer=checkpointer)
    """
    db_uri = _get_checkpointer_db_uri()

    logger.debug("Creating AsyncPostgresSaver", extra={"db_uri": db_uri[:30] + "..."})

    async with AsyncPostgresSaver.from_conn_string(db_uri) as checkpointer:
        # Setup создаёт таблицы если их нет
        # Вызываем только при первом использовании
        try:
            await checkpointer.setup()
            logger.info("Checkpointer tables initialized")
        except Exception as e:
            # Таблицы уже существуют или другая ошибка
            logger.debug("Checkpointer setup skipped", extra={"reason": str(e)})

        yield checkpointer


class CheckpointerManager:
    """
    Менеджер checkpointer для использования в lifespan.

    Держит соединение открытым на протяжении жизни приложения.
    """

    def __init__(self) -> None:
        self._checkpointer: AsyncPostgresSaver | None = None
        self._context: Any = None

    async def start(self) -> AsyncPostgresSaver:
        """Запустить checkpointer."""
        if self._checkpointer is not None:
            return self._checkpointer

        db_uri = _get_checkpointer_db_uri()

        logger.info("Starting CheckpointerManager")

        self._context = AsyncPostgresSaver.from_conn_string(db_uri)
        self._checkpointer = await self._context.__aenter__()

        try:
            await self._checkpointer.setup()
            logger.info("Checkpointer ready")
        except Exception as e:
            logger.debug("Checkpointer setup note", extra={"message": str(e)})

        return self._checkpointer

    async def stop(self) -> None:
        """Остановить checkpointer."""
        if self._context is not None:
            try:
                await self._context.__aexit__(None, None, None)
                logger.info("CheckpointerManager stopped")
            except Exception as e:
                logger.warning("Error stopping checkpointer", extra={"error": str(e)})
            finally:
                self._checkpointer = None
                self._context = None

    @property
    def checkpointer(self) -> AsyncPostgresSaver | None:
        """Получить текущий checkpointer."""
        return self._checkpointer
