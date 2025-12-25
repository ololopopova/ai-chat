"""Unit of Work pattern для управления транзакциями.

Предоставляет единую точку входа для работы с репозиториями
и гарантирует атомарность операций.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_session_factory
from src.repositories.chunk_repository import ChunkRepository
from src.repositories.conversation_repository import ConversationRepository
from src.repositories.domain_repository import DomainRepository
from src.repositories.job_repository import JobRepository

if TYPE_CHECKING:
    from src.db.session import AsyncSessionFactory

logger = logging.getLogger(__name__)


class UnitOfWork:
    """
    Unit of Work для группировки операций в одну транзакцию.

    Предоставляет доступ ко всем репозиториям через единую сессию,
    обеспечивая атомарность изменений.

    Example:
        async with UnitOfWork() as uow:
            domain = await uow.domains.create_domain(name="Test", ...)
            await uow.chunks.create_chunk(domain_id=domain.id, ...)
            await uow.commit()  # Обе операции атомарны
    """

    def __init__(self, session_factory: "AsyncSessionFactory | None" = None) -> None:
        """
        Инициализировать Unit of Work.

        Args:
            session_factory: Фабрика сессий (опционально, по умолчанию глобальная).
        """
        self._session_factory = session_factory or get_session_factory()
        self._session: AsyncSession | None = None

        # Ленивая инициализация репозиториев
        self._domains: DomainRepository | None = None
        self._chunks: ChunkRepository | None = None
        self._conversations: ConversationRepository | None = None
        self._jobs: JobRepository | None = None

    async def __aenter__(self) -> "UnitOfWork":
        """Начать транзакцию."""
        self._session = self._session_factory._session_factory()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Завершить транзакцию (rollback при ошибке)."""
        if self._session is None:
            return

        if exc_type is not None:
            await self.rollback()
            logger.debug("UnitOfWork rolled back due to exception", exc_info=exc_val)
        await self._session.close()
        self._session = None

    @property
    def session(self) -> AsyncSession:
        """Получить текущую сессию."""
        if self._session is None:
            msg = "UnitOfWork must be used as async context manager"
            raise RuntimeError(msg)
        return self._session

    # ==========================================
    # Репозитории (ленивая инициализация)
    # ==========================================

    @property
    def domains(self) -> DomainRepository:
        """Репозиторий доменов."""
        if self._domains is None:
            self._domains = DomainRepository(self.session)
        return self._domains

    @property
    def chunks(self) -> ChunkRepository:
        """Репозиторий чанков."""
        if self._chunks is None:
            self._chunks = ChunkRepository(self.session)
        return self._chunks

    @property
    def conversations(self) -> ConversationRepository:
        """Репозиторий диалогов."""
        if self._conversations is None:
            self._conversations = ConversationRepository(self.session)
        return self._conversations

    @property
    def jobs(self) -> JobRepository:
        """Репозиторий задач."""
        if self._jobs is None:
            self._jobs = JobRepository(self.session)
        return self._jobs

    # ==========================================
    # Управление транзакцией
    # ==========================================

    async def commit(self) -> None:
        """Зафиксировать транзакцию."""
        await self.session.commit()
        logger.debug("UnitOfWork committed")

    async def rollback(self) -> None:
        """Откатить транзакцию."""
        await self.session.rollback()
        logger.debug("UnitOfWork rolled back")

    async def flush(self) -> None:
        """Сбросить изменения в БД без commit."""
        await self.session.flush()


@asynccontextmanager
async def get_unit_of_work() -> AsyncGenerator[UnitOfWork]:
    """
    Dependency для получения UnitOfWork.

    Yields:
        UnitOfWork instance.

    Example:
        async with get_unit_of_work() as uow:
            await uow.domains.create_domain(...)
            await uow.commit()
    """
    async with UnitOfWork() as uow:
        yield uow
