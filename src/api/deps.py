"""Dependency injection для FastAPI."""

from collections.abc import AsyncGenerator
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import yaml
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings, get_settings

if TYPE_CHECKING:
    from src.repositories.chunk_repository import ChunkRepository
    from src.repositories.conversation_repository import ConversationRepository
    from src.repositories.domain_repository import DomainRepository
    from src.repositories.job_repository import JobRepository
    from src.repositories.unit_of_work import UnitOfWork


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


# ==========================================
# Database Dependencies
# ==========================================


async def get_db_session() -> AsyncGenerator[AsyncSession]:
    """
    Dependency для получения async database session.

    Yields:
        AsyncSession для работы с БД.

    Example:
        @router.get("/items")
        async def get_items(session: AsyncSession = Depends(get_db_session)):
            ...
    """
    from src.db.session import get_session

    async for session in get_session():
        yield session


# Type alias для краткости в route handlers
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


async def get_domain_repository(
    session: DbSession,
) -> "DomainRepository":
    """
    Dependency для получения DomainRepository.

    Args:
        session: AsyncSession (инжектится автоматически через Depends).

    Returns:
        DomainRepository instance.
    """
    from src.repositories.domain_repository import DomainRepository

    return DomainRepository(session)


async def get_chunk_repository(
    session: DbSession,
) -> "ChunkRepository":
    """
    Dependency для получения ChunkRepository.

    Args:
        session: AsyncSession (инжектится автоматически через Depends).

    Returns:
        ChunkRepository instance.
    """
    from src.repositories.chunk_repository import ChunkRepository

    return ChunkRepository(session)


async def get_conversation_repository(
    session: DbSession,
) -> "ConversationRepository":
    """
    Dependency для получения ConversationRepository.

    Args:
        session: AsyncSession (инжектится автоматически через Depends).

    Returns:
        ConversationRepository instance.
    """
    from src.repositories.conversation_repository import ConversationRepository

    return ConversationRepository(session)


async def get_job_repository(
    session: DbSession,
) -> "JobRepository":
    """
    Dependency для получения JobRepository.

    Args:
        session: AsyncSession (инжектится автоматически через Depends).

    Returns:
        JobRepository instance.
    """
    from src.repositories.job_repository import JobRepository

    return JobRepository(session)


async def get_unit_of_work() -> AsyncGenerator["UnitOfWork"]:
    """
    Dependency для получения UnitOfWork.

    Предоставляет единую точку входа для работы с несколькими
    репозиториями в рамках одной транзакции.

    Yields:
        UnitOfWork instance.

    Example:
        @router.post("/domains/{id}/ingest")
        async def ingest_domain(
            uow: UnitOfWork = Depends(get_unit_of_work),
        ):
            domain = await uow.domains.get(id)
            await uow.chunks.delete_by_domain(id)
            # ... create new chunks
            await uow.commit()
    """
    from src.repositories.unit_of_work import UnitOfWork

    async with UnitOfWork() as uow:
        yield uow


# Type aliases для использования в route handlers
DomainRepo = Annotated["DomainRepository", Depends(get_domain_repository)]
ChunkRepo = Annotated["ChunkRepository", Depends(get_chunk_repository)]
ConversationRepo = Annotated[
    "ConversationRepository", Depends(get_conversation_repository)
]
JobRepo = Annotated["JobRepository", Depends(get_job_repository)]
UoW = Annotated["UnitOfWork", Depends(get_unit_of_work)]
