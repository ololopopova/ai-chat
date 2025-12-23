"""Pydantic модели событий WebSocket и сообщений чата."""

from datetime import datetime
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """Роль автора сообщения."""

    USER = "user"
    ASSISTANT = "assistant"


class ChatMessage(BaseModel):
    """Модель сообщения в чате."""

    model_config = {"use_enum_values": True}

    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    asset_url: str | None = None


class StageName(str, Enum):
    """Названия стадий обработки запроса."""

    ROUTER = "router"
    CLARIFY = "clarify"
    RETRIEVE = "retrieve"
    GENERATE = "generate"
    OFF_TOPIC = "off_topic"
    TOOL_SELECT = "tool_select"
    TOOL_EXECUTE = "tool_execute"


# Русские названия стадий для отображения
STAGE_LABELS: dict[StageName, str] = {
    StageName.ROUTER: "Определение темы",
    StageName.CLARIFY: "Уточнение вопроса",
    StageName.RETRIEVE: "Поиск информации",
    StageName.GENERATE: "Формирование ответа",
    StageName.OFF_TOPIC: "Вопрос вне темы",
    StageName.TOOL_SELECT: "Выбор инструмента",
    StageName.TOOL_EXECUTE: "Выполнение инструмента",
}


class StageStatus(str, Enum):
    """Статус стадии обработки."""

    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"


class EventType(str, Enum):
    """Типы событий WebSocket."""

    STAGE = "stage"
    TOKEN = "token"
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
    PROGRESS = "progress"
    ERROR = "error"
    COMPLETE = "complete"


class StageEvent(BaseModel):
    """Событие смены стадии обработки."""

    type: Literal[EventType.STAGE] = EventType.STAGE
    stage_name: StageName
    message: str | None = None


class TokenEvent(BaseModel):
    """Событие токена (стриминг ответа)."""

    type: Literal[EventType.TOKEN] = EventType.TOKEN
    content: str


class ToolStartEvent(BaseModel):
    """Событие начала вызова инструмента."""

    type: Literal[EventType.TOOL_START] = EventType.TOOL_START
    tool_name: str
    tool_input: dict[str, str] | None = None


class ToolEndEvent(BaseModel):
    """Событие окончания вызова инструмента."""

    type: Literal[EventType.TOOL_END] = EventType.TOOL_END
    tool_name: str
    success: bool
    result: str | None = None
    error: str | None = None
    asset_url: str | None = None


class ProgressEvent(BaseModel):
    """Событие прогресса долгой операции."""

    type: Literal[EventType.PROGRESS] = EventType.PROGRESS
    job_id: str
    progress: Annotated[int, Field(ge=0, le=100)]
    current_step: str


class ErrorEvent(BaseModel):
    """Событие ошибки."""

    type: Literal[EventType.ERROR] = EventType.ERROR
    message: str
    code: str | None = None


class CompleteEvent(BaseModel):
    """Событие завершения обработки."""

    type: Literal[EventType.COMPLETE] = EventType.COMPLETE
    final_response: str | None = None
    asset_url: str | None = None


# Объединённый тип для всех событий
StreamEvent = (
    StageEvent
    | TokenEvent
    | ToolStartEvent
    | ToolEndEvent
    | ProgressEvent
    | ErrorEvent
    | CompleteEvent
)
