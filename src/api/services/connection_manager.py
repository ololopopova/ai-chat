"""Менеджер WebSocket соединений."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.logging import get_logger

if TYPE_CHECKING:
    from fastapi import WebSocket

logger = get_logger(__name__)


class ConnectionManager:
    """
    Менеджер активных WebSocket соединений.

    Note:
        В текущей реализации работает только в рамках одного процесса.
        Для multi-worker deployment нужен shared state через Redis.
    """

    def __init__(self) -> None:
        """Инициализация менеджера соединений."""
        # thread_id -> WebSocket
        self._active_connections: dict[str, WebSocket] = {}

    async def connect(self, thread_id: str, websocket: WebSocket) -> None:
        """
        Принять новое WebSocket соединение.

        Args:
            thread_id: ID сессии диалога
            websocket: WebSocket соединение
        """
        await websocket.accept()
        self._active_connections[thread_id] = websocket
        logger.info(
            "WebSocket connected",
            extra={
                "thread_id": thread_id,
                "active_connections": len(self._active_connections),
            },
        )

    def disconnect(self, thread_id: str) -> None:
        """
        Отключить WebSocket соединение.

        Args:
            thread_id: ID сессии диалога
        """
        if thread_id in self._active_connections:
            del self._active_connections[thread_id]
            logger.info(
                "WebSocket disconnected",
                extra={
                    "thread_id": thread_id,
                    "active_connections": len(self._active_connections),
                },
            )

    def get_websocket(self, thread_id: str) -> WebSocket | None:
        """Получить WebSocket по thread_id."""
        return self._active_connections.get(thread_id)

    def is_connected(self, thread_id: str) -> bool:
        """Проверить, активно ли соединение."""
        return thread_id in self._active_connections

    @property
    def active_count(self) -> int:
        """Количество активных соединений."""
        return len(self._active_connections)

    def get_all_thread_ids(self) -> list[str]:
        """Получить список всех активных thread_id."""
        return list(self._active_connections.keys())
