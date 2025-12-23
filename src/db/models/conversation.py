"""Модель Conversation — история диалогов.

Conversation хранит историю сообщений и состояние LangGraph.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base, TimestampMixin


class Conversation(Base, TimestampMixin):
    """
    Модель диалога.

    Attributes:
        id: UUID первичный ключ.
        thread_id: Внешний идентификатор thread (для LangGraph).
        title: Заголовок диалога (может генерироваться автоматически).
        messages: История сообщений в формате JSONB.
        state: Состояние LangGraph в формате JSONB.
        created_at: Время создания.
        updated_at: Время последнего обновления.

    Note:
        messages хранятся как JSONB массив:
        [
            {"role": "user", "content": "Привет!", "timestamp": "..."},
            {"role": "assistant", "content": "Здравствуйте!", "timestamp": "..."},
            ...
        ]
    """

    # Внешний идентификатор thread
    thread_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        comment="Внешний идентификатор thread",
    )

    # Заголовок диалога
    title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Заголовок диалога",
    )

    # История сообщений
    messages: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment="История сообщений",
    )

    # Состояние LangGraph
    state: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        default=None,
        comment="Состояние LangGraph",
    )

    # Timestamps из TimestampMixin
    updated_at: Mapped[datetime]

    # Индексы
    __table_args__ = (Index("ix_conversations_created_at", "created_at"),)

    def __repr__(self) -> str:
        """Строковое представление диалога."""
        title = self.title or "Без заголовка"
        return f"<Conversation(id={self.id}, thread_id='{self.thread_id}', title='{title}')>"

    @property
    def message_count(self) -> int:
        """Количество сообщений в диалоге."""
        return len(self.messages) if self.messages else 0

    def add_message(self, role: str, content: str, **extra: Any) -> None:
        """
        Добавить сообщение в историю.

        Args:
            role: Роль отправителя (user, assistant, system).
            content: Содержимое сообщения.
            **extra: Дополнительные поля (timestamp и т.д.).
        """
        from datetime import UTC, datetime

        if self.messages is None:
            self.messages = []

        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(UTC).isoformat(),
            **extra,
        }
        self.messages.append(message)
