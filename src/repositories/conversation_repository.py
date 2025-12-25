"""Репозиторий для работы с диалогами.

Реализует CRUD и upsert для Conversation модели.
"""

from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.conversation import Conversation
from src.repositories.base import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    """
    Репозиторий для работы с диалогами.

    Расширяет BaseRepository методами для:
    - Поиска по thread_id
    - Upsert операций
    - Работы с сообщениями
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Инициализировать репозиторий.

        Args:
            session: AsyncSession для работы с БД.
        """
        super().__init__(Conversation, session)

    async def get_by_thread(self, thread_id: str) -> Conversation | None:
        """
        Получить диалог по thread_id.

        Args:
            thread_id: Внешний идентификатор thread.

        Returns:
            Conversation или None, если не найден.
        """
        stmt = select(Conversation).where(Conversation.thread_id == thread_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert(
        self,
        thread_id: str,
        *,
        title: str | None = None,
        messages: list[dict[str, Any]] | None = None,
        state: dict[str, Any] | None = None,
    ) -> Conversation:
        """
        Создать или обновить диалог.

        Args:
            thread_id: Внешний идентификатор thread.
            title: Заголовок диалога.
            messages: История сообщений.
            state: Состояние LangGraph.

        Returns:
            Созданный или обновлённый диалог.
        """
        from datetime import UTC, datetime

        now = datetime.now(UTC)

        # Подготовка данных для вставки
        insert_data: dict[str, Any] = {
            "thread_id": thread_id,
            "created_at": now,
            "updated_at": now,
        }

        if title is not None:
            insert_data["title"] = title
        if messages is not None:
            insert_data["messages"] = messages
        else:
            insert_data["messages"] = []
        if state is not None:
            insert_data["state"] = state

        # Подготовка данных для обновления (без thread_id и created_at)
        update_data: dict[str, Any] = {"updated_at": now}
        if title is not None:
            update_data["title"] = title
        if messages is not None:
            update_data["messages"] = messages
        if state is not None:
            update_data["state"] = state

        # PostgreSQL upsert
        stmt = (
            insert(Conversation)
            .values(**insert_data)
            .on_conflict_do_update(
                index_elements=["thread_id"],
                set_=update_data,
            )
            .returning(Conversation)
        )

        result = await self.session.execute(stmt)
        await self.session.flush()

        return result.scalar_one()

    async def add_message(
        self,
        thread_id: str,
        role: str,
        content: str,
        **extra: Any,
    ) -> Conversation | None:
        """
        Добавить сообщение в диалог.

        Args:
            thread_id: Внешний идентификатор thread.
            role: Роль отправителя.
            content: Содержимое сообщения.
            **extra: Дополнительные поля.

        Returns:
            Обновлённый диалог или None, если не найден.
        """
        from datetime import UTC, datetime

        conversation = await self.get_by_thread(thread_id)
        if conversation is None:
            return None

        # Добавляем сообщение
        conversation.add_message(role, content, **extra)
        conversation.updated_at = datetime.now(UTC)

        await self.session.flush()
        return conversation

    async def update_state(
        self,
        thread_id: str,
        state: dict[str, Any],
    ) -> Conversation | None:
        """
        Обновить состояние LangGraph.

        Args:
            thread_id: Внешний идентификатор thread.
            state: Новое состояние.

        Returns:
            Обновлённый диалог или None, если не найден.
        """
        from datetime import UTC, datetime

        conversation = await self.get_by_thread(thread_id)
        if conversation is None:
            return None

        conversation.state = state
        conversation.updated_at = datetime.now(UTC)

        await self.session.flush()
        return conversation

    async def delete_by_thread(self, thread_id: str) -> bool:
        """
        Удалить диалог по thread_id.

        Args:
            thread_id: Внешний идентификатор thread.

        Returns:
            True если удалён, False если не найден.
        """
        stmt = delete(Conversation).where(Conversation.thread_id == thread_id)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return bool(result.rowcount and result.rowcount > 0)  # type: ignore[attr-defined]

    async def get_recent(
        self,
        *,
        limit: int = 10,
    ) -> list[Conversation]:
        """
        Получить недавние диалоги.

        Args:
            limit: Максимальное количество результатов.

        Returns:
            Список диалогов, отсортированных по updated_at DESC.
        """
        stmt = (
            select(Conversation).order_by(Conversation.updated_at.desc()).limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def clear_messages(self, thread_id: str) -> Conversation | None:
        """
        Очистить историю сообщений диалога.

        Args:
            thread_id: Внешний идентификатор thread.

        Returns:
            Обновлённый диалог или None.
        """
        from datetime import UTC, datetime

        conversation = await self.get_by_thread(thread_id)
        if conversation is None:
            return None

        conversation.messages = []
        conversation.state = None
        conversation.updated_at = datetime.now(UTC)

        await self.session.flush()
        return conversation
