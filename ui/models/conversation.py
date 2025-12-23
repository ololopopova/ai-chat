"""Модель диалога (conversation) для хранения в session_state."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui.models.events import ChatMessage


@dataclass
class Conversation:
    """Данные одного диалога."""

    thread_id: str
    title: str = "Новый диалог"
    messages: list[ChatMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    def get_title(self, max_length: int = 30) -> str:
        """
        Получить заголовок диалога.

        Если есть сообщения — берём первое сообщение пользователя.
        Иначе — "Новый диалог".

        Args:
            max_length: Максимальная длина заголовка

        Returns:
            Заголовок диалога
        """
        if not self.messages:
            return self.title

        # Ищем первое сообщение пользователя
        for msg in self.messages:
            role = msg.role.value if hasattr(msg.role, "value") else msg.role
            if role == "user":
                title = msg.content[:max_length]
                if len(msg.content) > max_length:
                    title += "..."
                return title

        return self.title
