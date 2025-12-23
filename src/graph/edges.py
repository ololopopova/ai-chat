"""Conditional edges для графа."""

from __future__ import annotations

from typing import Literal

from src.core.logging import get_logger
from src.graph.state import ChatState, Route

logger = get_logger(__name__)


def route_after_router(state: ChatState) -> Literal["generate", "clarify", "off_topic"]:
    """
    Conditional edge после router node.

    Определяет следующий узел на основе результата маршрутизации.

    Args:
        state: Текущее состояние графа

    Returns:
        Имя следующего узла: "generate", "clarify" или "off_topic"
    """
    route = state.get("route")

    if route == Route.GENERATE:
        logger.debug("Routing to generate")
        return "generate"
    elif route == Route.CLARIFY:
        logger.debug("Routing to clarify")
        return "clarify"
    else:
        logger.debug("Routing to off_topic")
        return "off_topic"

