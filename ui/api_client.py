"""Интерфейс API клиента для UI."""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from pydantic import ValidationError

from src.core.config import get_settings
from src.core.logging import get_logger
from ui.models.events import (
    CompleteEvent,
    ErrorEvent,
    EventType,
    ProgressEvent,
    StageEvent,
    StageName,
    StreamEvent,
    TokenEvent,
    ToolEndEvent,
    ToolStartEvent,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

logger = get_logger(__name__)


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
        Отправить сообщение и получить поток событий (асинхронно).

        Args:
            message: Текст сообщения пользователя

        Yields:
            StreamEvent события от backend
        """
        ...

    def send_message_sync(self, message: str) -> Iterator[StreamEvent]:
        """
        Отправить сообщение и получить поток событий (синхронно).

        Args:
            message: Текст сообщения пользователя

        Yields:
            StreamEvent события от backend
        """
        ...


class WebSocketAPIClient:
    """
    Реальный API клиент, использующий WebSocket для связи с backend.

    Подключается к FastAPI backend и стримит события в реальном времени.

    ВАЖНО: Создаёт новое WebSocket соединение для каждого сообщения.
    Это необходимо для корректной работы со Streamlit, который создаёт
    новый asyncio event loop при каждом rerun скрипта.

    Example:
        client = WebSocketAPIClient()
        client.create_thread()
        async for event in client.send_message("Hello"):
            print(event)
    """

    # Таймауты
    CONNECT_TIMEOUT: float = 10.0
    RECEIVE_TIMEOUT: float = 120.0

    def __init__(self, ws_url: str | None = None) -> None:
        """
        Инициализация WebSocket клиента.

        Args:
            ws_url: Базовый URL WebSocket сервера.
                    Если None, берётся из настроек.
        """
        settings = get_settings()
        self._ws_url = ws_url or settings.api_ws_url
        self._current_thread_id: str | None = None

    def create_thread(self) -> str:
        """
        Создать новый thread (сессию диалога).

        Returns:
            Уникальный идентификатор thread
        """
        self._current_thread_id = str(uuid.uuid4())
        return self._current_thread_id

    @property
    def thread_id(self) -> str | None:
        """Текущий thread_id."""
        return self._current_thread_id

    async def send_message(self, message: str) -> AsyncIterator[StreamEvent]:
        """
        Отправить сообщение и получить поток событий.

        Создаёт новое WebSocket соединение для каждого сообщения
        и закрывает после завершения. Это необходимо для корректной
        работы со Streamlit.

        Args:
            message: Текст сообщения пользователя

        Yields:
            StreamEvent события от backend
        """
        import websockets

        if not self._current_thread_id:
            self._current_thread_id = str(uuid.uuid4())

        url = f"{self._ws_url}/ws/chat/{self._current_thread_id}"

        try:
            # Создаём НОВОЕ соединение для этого сообщения
            logger.info(
                "Opening WebSocket connection",
                extra={"url": url, "thread_id": self._current_thread_id[:8]},
            )

            async with websockets.connect(
                url,
                open_timeout=self.CONNECT_TIMEOUT,
                close_timeout=5.0,
            ) as websocket:
                # Отправляем сообщение
                request = {
                    "type": "message",
                    "content": message,
                    "metadata": {},
                }
                await websocket.send(json.dumps(request))
                logger.info(
                    "Message sent",
                    extra={
                        "message_preview": message[:50],
                        "thread_id": self._current_thread_id[:8],
                    },
                )

                # Получаем события до complete или error
                while True:
                    try:
                        raw_data = await asyncio.wait_for(
                            websocket.recv(),
                            timeout=self.RECEIVE_TIMEOUT,
                        )

                        data = json.loads(raw_data)
                        event = self._parse_event(data)

                        if event:
                            yield event

                            # Завершаем при complete или error
                            if isinstance(event, (CompleteEvent, ErrorEvent)):
                                logger.info(
                                    "Message processing complete",
                                    extra={"thread_id": self._current_thread_id[:8]},
                                )
                                return

                    except TimeoutError:
                        logger.warning("Receive timeout")
                        yield ErrorEvent(
                            type=EventType.ERROR,
                            message="Response timeout",
                            code="TIMEOUT",
                        )
                        return

        except TimeoutError:
            logger.error("WebSocket connection timeout")
            yield ErrorEvent(
                type=EventType.ERROR,
                message="Failed to connect to server (timeout)",
                code="CONNECTION_TIMEOUT",
            )

        except Exception as e:
            logger.exception("Error during message processing")
            yield ErrorEvent(
                type=EventType.ERROR,
                message=f"Connection error: {e}",
                code="CONNECTION_ERROR",
            )

    def send_message_sync(self, message: str) -> Iterator[StreamEvent]:
        """
        Синхронная версия send_message для Streamlit.

        Streamlit не обновляет UI внутри asyncio.run(), поэтому
        используем синхронный WebSocket клиент.

        Args:
            message: Текст сообщения пользователя

        Yields:
            StreamEvent события от backend
        """
        from websocket import WebSocketTimeoutException, create_connection

        if not self._current_thread_id:
            self._current_thread_id = str(uuid.uuid4())

        # Преобразуем ws:// в http:// для websocket-client
        url = f"{self._ws_url}/ws/chat/{self._current_thread_id}"

        try:
            logger.info(
                "Opening sync WebSocket connection",
                extra={"url": url, "thread_id": self._current_thread_id[:8]},
            )

            ws = create_connection(
                url,
                timeout=self.CONNECT_TIMEOUT,
            )

            try:
                # Отправляем сообщение
                request = {
                    "type": "message",
                    "content": message,
                    "metadata": {},
                }
                ws.send(json.dumps(request))
                logger.info(
                    "Message sent (sync)",
                    extra={
                        "message_preview": message[:50],
                        "thread_id": self._current_thread_id[:8],
                    },
                )

                # Устанавливаем таймаут на получение
                ws.settimeout(self.RECEIVE_TIMEOUT)

                # Получаем события до complete или error
                while True:
                    try:
                        raw_data = ws.recv()
                        data = json.loads(raw_data)
                        event = self._parse_event(data)

                        if event:
                            yield event

                            # Завершаем при complete или error
                            if isinstance(event, (CompleteEvent, ErrorEvent)):
                                logger.info(
                                    "Message processing complete (sync)",
                                    extra={"thread_id": self._current_thread_id[:8]},
                                )
                                return

                    except WebSocketTimeoutException:
                        logger.warning("Receive timeout (sync)")
                        yield ErrorEvent(
                            type=EventType.ERROR,
                            message="Response timeout",
                            code="TIMEOUT",
                        )
                        return

            finally:
                ws.close()

        except Exception as e:
            logger.exception("Error during sync message processing")
            yield ErrorEvent(
                type=EventType.ERROR,
                message=f"Connection error: {e}",
                code="CONNECTION_ERROR",
            )

    def _parse_event(self, data: dict[str, Any]) -> StreamEvent | None:
        """
        Преобразовать словарь в типизированное событие.

        Args:
            data: Словарь с данными события

        Returns:
            Типизированное событие или None при ошибке парсинга
        """
        event_type = data.get("type")

        try:
            match event_type:
                case "stage":
                    # Преобразуем stage_name в enum
                    stage_name_str = data.get("stage_name", "")
                    try:
                        stage_name = StageName(stage_name_str)
                    except ValueError:
                        logger.warning(
                            "Unknown stage name",
                            extra={"stage_name": stage_name_str},
                        )
                        stage_name = StageName.ROUTER

                    return StageEvent(
                        type=EventType.STAGE,
                        stage_name=stage_name,
                        message=data.get("message"),
                    )

                case "token":
                    return TokenEvent(
                        type=EventType.TOKEN,
                        content=data.get("content", ""),
                    )

                case "tool_start":
                    return ToolStartEvent(
                        type=EventType.TOOL_START,
                        tool_name=data.get("tool_name", ""),
                        tool_input=data.get("tool_input"),
                    )

                case "tool_end":
                    return ToolEndEvent(
                        type=EventType.TOOL_END,
                        tool_name=data.get("tool_name", ""),
                        success=data.get("success", False),
                        result=data.get("result"),
                        error=data.get("error"),
                        asset_url=data.get("asset_url"),
                    )

                case "progress":
                    return ProgressEvent(
                        type=EventType.PROGRESS,
                        job_id=data.get("job_id", ""),
                        progress=data.get("progress", 0),
                        current_step=data.get("current_step", ""),
                    )

                case "error":
                    return ErrorEvent(
                        type=EventType.ERROR,
                        message=data.get("message", "Unknown error"),
                        code=data.get("code"),
                    )

                case "complete":
                    return CompleteEvent(
                        type=EventType.COMPLETE,
                        final_response=data.get("final_response"),
                        asset_url=data.get("asset_url"),
                    )

                case _:
                    logger.warning(
                        "Unknown event type",
                        extra={"event_type": event_type},
                    )
                    return None

        except ValidationError as e:
            logger.warning(
                "Event validation error",
                extra={"error": str(e), "data": data},
            )
            return None


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

    return WebSocketAPIClient()
