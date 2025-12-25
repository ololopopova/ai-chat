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
    from src.api.services import ConnectionManager
    from src.core.config import Settings
    from src.services.chat_service import ChatService

router = APIRouter()
logger = get_logger(__name__)


def _get_services(
    websocket: WebSocket,
) -> tuple[Settings, ConnectionManager, ChatService | None]:
    """
    Получить сервисы из app.state.

    Args:
        websocket: WebSocket соединение (для доступа к app)

    Returns:
        Tuple (settings, connection_manager, chat_service)
    """
    app = websocket.app
    return (
        app.state.settings,
        app.state.connection_manager,
        getattr(app.state, "chat_service", None),
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
            {"type": "stage", "stage_name": "router", "message": "...", "status": "active"}
            {"type": "token", "content": "..."}
            {"type": "complete", "final_response": "...", "thread_id": "...", "asset_url": null}
            {"type": "error", "message": "...", "code": "...", "timestamp": "..."}
            {"type": "pong", "timestamp": "..."}
    """
    # Получаем сервисы через DI (из app.state)
    settings, connection_manager, chat_service = _get_services(websocket)

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

                # Обработка сообщения через ChatService (если доступен)
                if chat_service is not None:
                    async for event in chat_service.process_message(
                        message.content, thread_id
                    ):
                        # Сериализуем события в JSON
                        await websocket.send_json(event.to_dict())
                else:
                    # Fallback на echo режим если ChatService не инициализирован
                    logger.warning(
                        "ChatService not available, using fallback",
                        extra={"thread_id": thread_id[:8]},
                    )
                    await _fallback_echo_response(websocket, message.content, thread_id)

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


async def _fallback_echo_response(
    websocket: WebSocket,
    message: str,
    thread_id: str,
) -> None:
    """
    Fallback echo ответ когда ChatService недоступен.

    Args:
        websocket: WebSocket соединение
        message: Сообщение пользователя
        thread_id: ID сессии
    """
    # Stage event
    await websocket.send_json(
        {
            "type": "stage",
            "stage_name": "generate",
            "status": "active",
            "message": "Формирую ответ...",
        }
    )

    # Формируем echo ответ
    response = f"ChatService временно недоступен. Ваше сообщение: «{message}»"

    # Token events (посимвольно)
    for char in response:
        await websocket.send_json(
            {
                "type": "token",
                "content": char,
            }
        )
        await asyncio.sleep(0.01)

    # Complete event
    await websocket.send_json(
        {
            "type": "complete",
            "final_response": response,
            "thread_id": thread_id,
            "asset_url": None,
        }
    )
