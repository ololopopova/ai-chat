"""Состояние графа для чат-системы."""

from enum import Enum
from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages


class Route(str, Enum):
    """Возможные маршруты после роутера."""

    GENERATE = "generate"
    CLARIFY = "clarify"
    OFF_TOPIC = "off_topic"


class Stage(str, Enum):
    """Стадии обработки для UI timeline."""

    ROUTER = "router"
    CLARIFY = "clarify"
    RETRIEVE = "retrieve"
    GENERATE = "generate"
    OFF_TOPIC = "off_topic"


class ChatState(TypedDict, total=False):
    """
    Состояние графа обработки сообщений.

    Attributes:
        messages: История сообщений с add_messages reducer.
                  Автоматически объединяет новые сообщения с существующими.
        route: Результат маршрутизации (generate/clarify/off_topic).
        domain: Определённый домен знаний (slug).
        stage: Текущий этап обработки для UI.
        confidence: Уверенность роутера в определении домена (0.0-1.0).
        matched_domains: Список совпавших доменов (если несколько).
    """

    # Обязательное поле с reducer для автоматического merge сообщений
    messages: Annotated[list[Any], add_messages]

    # Результат маршрутизации
    route: Route | None

    # Определённый домен
    domain: str | None

    # Текущий этап для timeline UI
    stage: Stage | None

    # Метаданные маршрутизации
    confidence: float | None
    matched_domains: list[str] | None
