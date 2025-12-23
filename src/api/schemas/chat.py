"""Схемы для chat endpoints и WebSocket событий."""

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    """Получить текущее время в UTC."""
    return datetime.now(UTC)


class ChatMessageRequest(BaseModel):
    """Входящее сообщение от клиента через WebSocket."""

    type: Literal["message"] = "message"
    content: str = Field(..., min_length=1, max_length=10000)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"json_schema_extra": {
        "example": {
            "type": "message",
            "content": "Текст сообщения пользователя",
            "metadata": {},
        }
    }}


class ErrorResponse(BaseModel):
    """Ответ об ошибке через WebSocket."""

    type: Literal["error"] = "error"
    message: str
    code: str
    timestamp: datetime = Field(default_factory=_utc_now)

    model_config = {"json_schema_extra": {
        "example": {
            "type": "error",
            "message": "Описание ошибки",
            "code": "INVALID_MESSAGE",
            "timestamp": "2024-12-23T10:30:00Z",
        }
    }}


class PingMessage(BaseModel):
    """Ping сообщение для heartbeat."""

    type: Literal["ping"] = "ping"


class PongMessage(BaseModel):
    """Pong ответ на ping."""

    type: Literal["pong"] = "pong"
    timestamp: datetime = Field(default_factory=_utc_now)

