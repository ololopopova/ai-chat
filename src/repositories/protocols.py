"""Repository protocols (interfaces) for Dependency Inversion.

Определяет контракты для репозиториев, что позволяет:
- Легко мокировать в тестах
- Следовать принципу DIP (SOLID)
- Заменять реализации без изменения клиентского кода
"""

import uuid
from typing import Any, Literal, Protocol, runtime_checkable

# Тип для роли сообщения (соответствует формату в Conversation.messages)
MessageRole = Literal["user", "assistant", "system"]


@runtime_checkable
class RepositoryProtocol[T](Protocol):
    """Базовый протокол для репозитория."""

    async def get(self, id: uuid.UUID) -> T | None:
        """Получить запись по ID."""
        ...

    async def get_all(self, *, skip: int = 0, limit: int = 100) -> list[T]:
        """Получить список записей с пагинацией."""
        ...

    async def create(self, **data: Any) -> T:
        """Создать новую запись."""
        ...

    async def update(self, id: uuid.UUID, **data: Any) -> T | None:
        """Обновить запись по ID."""
        ...

    async def delete(self, id: uuid.UUID) -> bool:
        """Удалить запись по ID."""
        ...

    async def count(self) -> int:
        """Подсчитать общее количество записей."""
        ...

    async def exists(self, id: uuid.UUID) -> bool:
        """Проверить существование записи по ID."""
        ...


@runtime_checkable
class DomainRepositoryProtocol(Protocol):
    """Протокол для DomainRepository."""

    async def get(self, id: uuid.UUID) -> Any | None:
        """Получить домен по ID."""
        ...

    async def get_by_slug(self, slug: str) -> Any | None:
        """Получить домен по slug."""
        ...

    async def get_active(self, *, skip: int = 0, limit: int = 100) -> list[Any]:
        """Получить все активные домены."""
        ...

    async def create_domain(
        self,
        *,
        name: str,
        slug: str,
        google_doc_url: str,
        description: str | None = None,
        is_active: bool = True,
    ) -> Any:
        """Создать новый домен."""
        ...

    async def slug_exists(self, slug: str, exclude_id: uuid.UUID | None = None) -> bool:
        """Проверить существование slug."""
        ...


@runtime_checkable
class ChunkRepositoryProtocol(Protocol):
    """Протокол для ChunkRepository."""

    async def get(self, id: uuid.UUID) -> Any | None:
        """Получить чанк по ID."""
        ...

    async def search_fts(
        self,
        query: str,
        domain_id: uuid.UUID | None = None,
        *,
        limit: int = 10,
    ) -> list[tuple[Any, float]]:
        """Полнотекстовый поиск."""
        ...

    async def search_vector(
        self,
        embedding: list[float],
        domain_id: uuid.UUID | None = None,
        *,
        limit: int = 10,
    ) -> list[tuple[Any, float]]:
        """Векторный поиск."""
        ...

    async def create_chunk(
        self,
        *,
        domain_id: uuid.UUID,
        content: str,
        chunk_index: int,
        embedding: list[float] | None = None,
        chunk_metadata: dict[str, Any] | None = None,
    ) -> Any:
        """Создать новый чанк."""
        ...

    async def delete_by_domain(self, domain_id: uuid.UUID) -> int:
        """Удалить все чанки домена."""
        ...


@runtime_checkable
class ConversationRepositoryProtocol(Protocol):
    """Протокол для ConversationRepository."""

    async def get(self, id: uuid.UUID) -> Any | None:
        """Получить диалог по ID."""
        ...

    async def get_by_session(self, session_id: str) -> Any | None:
        """Получить диалог по session_id."""
        ...

    async def add_message(
        self,
        conversation_id: uuid.UUID,
        role: MessageRole,
        content: str,
    ) -> Any:
        """Добавить сообщение в диалог."""
        ...


@runtime_checkable
class JobRepositoryProtocol(Protocol):
    """Протокол для JobRepository."""

    async def get(self, id: uuid.UUID) -> Any | None:
        """Получить задачу по ID."""
        ...

    async def create_job(
        self,
        *,
        tool_name: str,
        input_data: dict[str, Any],
        conversation_id: uuid.UUID | None = None,
    ) -> Any:
        """Создать новую задачу."""
        ...

    async def update_progress(
        self,
        id: uuid.UUID,
        *,
        progress: int,
        current_step: str | None = None,
    ) -> Any | None:
        """Обновить прогресс задачи."""
        ...
