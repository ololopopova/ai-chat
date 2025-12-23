"""Интерфейс API клиента для UI."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from ui.models.events import StreamEvent


@runtime_checkable
class BaseApiClient(Protocol):
    """
    Протокол для API клиентов.

    Определяет интерфейс, который должны реализовать
    как mock-клиент, так и реальный клиент.
    """

    def create_thread(self) -> str:
        """
        Создать новый thread (сессию диалога).

        Returns:
            Уникальный идентификатор thread
        """
        ...

    @property
    def thread_id(self) -> str | None:
        """Текущий thread_id."""
        ...

    def send_message(self, message: str) -> AsyncIterator[StreamEvent]:
        """
        Отправить сообщение и получить поток событий.

        Args:
            message: Текст сообщения пользователя

        Yields:
            StreamEvent события от backend
        """
        ...


def get_api_client(use_mock: bool = True) -> BaseApiClient:
    """
    Фабрика для получения API клиента.

    Args:
        use_mock: Использовать mock клиент вместо реального

    Returns:
        Экземпляр API клиента
    """
    if use_mock:
        from ui.mock.mock_client import MockApiClient

        return MockApiClient()

    # TODO: Реализовать реальный клиент в будущих фазах
    from ui.mock.mock_client import MockApiClient

    return MockApiClient()
