"""WebSocket endpoint для чата."""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from src.api.schemas.chat import ChatMessageRequest, ErrorResponse, PongMessage
from src.core.logging import get_logger, set_thread_id

if TYPE_CHECKING:
    from src.api.services import ConnectionManager, MessageHandler
    from src.core.config import Settings

router = APIRouter()
logger = get_logger(__name__)


def _get_services(websocket: WebSocket) -> tuple[Settings, ConnectionManager, MessageHandler]:
    """
    Получить сервисы из app.state.

    Args:
        websocket: WebSocket соединение (для доступа к app)

    Returns:
        Tuple (settings, connection_manager, message_handler)
    """
    app = websocket.app
    return (
        app.state.settings,
        app.state.connection_manager,
        app.state.message_handler,
    )


@router.websocket("/ws/chat/{thread_id}")
async def websocket_chat(websocket: WebSocket, thread_id: str) -> None:
    """
    WebSocket endpoint для чата.

    Args:
        websocket: WebSocket соединение
        thread_id: UUID сессии диалога

    Protocol:
        Client -> Server:
            {"type": "message", "content": "text", "metadata": {}}
            {"type": "ping"}

        Server -> Client:
            {"type": "stage", "stage_name": "router", "message": "..."}
            {"type": "token", "content": "..."}
            {"type": "complete", "final_response": "...", "asset_url": null}
            {"type": "error", "message": "...", "code": "...", "timestamp": "..."}
            {"type": "pong", "timestamp": "..."}
    """
    # Получаем сервисы через DI (из app.state)
    settings, connection_manager, message_handler = _get_services(websocket)

    # Валидация thread_id (должен быть валидным UUID или создаём новый)
    try:
        uuid.UUID(thread_id)
    except ValueError:
        thread_id = str(uuid.uuid4())
        logger.warning(
            "Invalid thread_id provided, generated new",
            extra={"new_thread_id": thread_id[:8]},
        )

    # Устанавливаем thread_id в контекст для автоматического логирования
    set_thread_id(thread_id)

    await connection_manager.connect(thread_id, websocket)

    try:
        while True:
            try:
                # Получаем сообщение с таймаутом
                raw_data = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=settings.ws_connection_timeout,
                )

                # Проверяем размер сообщения (корректно через JSON)
                message_size = len(json.dumps(raw_data))
                if message_size > settings.ws_message_max_size:
                    error = ErrorResponse(
                        message="Message too large",
                        code="MESSAGE_TOO_LARGE",
                        timestamp=datetime.now(UTC),
                    )
                    await websocket.send_json(error.model_dump(mode="json"))
                    continue

                # Обработка ping
                if raw_data.get("type") == "ping":
                    pong = PongMessage(timestamp=datetime.now(UTC))
                    await websocket.send_json(pong.model_dump(mode="json"))
                    continue

                # Валидация сообщения
                try:
                    message = ChatMessageRequest.model_validate(raw_data)
                except ValidationError as e:
                    error = ErrorResponse(
                        message=f"Invalid message format: {e.error_count()} errors",
                        code="INVALID_MESSAGE",
                        timestamp=datetime.now(UTC),
                    )
                    await websocket.send_json(error.model_dump(mode="json"))
                    logger.warning(
                        "Invalid WebSocket message",
                        extra={"thread_id": thread_id, "errors": e.errors()},
                    )
                    continue

                # Обработка сообщения и стриминг событий через DI handler
                async for event in message_handler.process_message(message.content, thread_id):
                    # Сериализуем Pydantic модели в JSON
                    await websocket.send_json(event.model_dump(mode="json"))

            except TimeoutError:
                # Таймаут соединения
                logger.info(
                    "Connection timeout",
                    extra={"thread_id": thread_id[:8]},
                )
                break

    except WebSocketDisconnect:
        logger.info(
            "Client disconnected",
            extra={"thread_id": thread_id[:8]},
        )

    except Exception:
        logger.exception(
            "WebSocket error",
            extra={"thread_id": thread_id[:8]},
        )
        try:
            error = ErrorResponse(
                message="Internal server error",
                code="INTERNAL_ERROR",
                timestamp=datetime.now(UTC),
            )
            await websocket.send_json(error.model_dump(mode="json"))
        except Exception:
            pass  # Соединение могло быть уже закрыто

    finally:
        connection_manager.disconnect(thread_id)
