"""Сборка графа LangGraph."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from langgraph.graph import END, START, StateGraph

from src.core.logging import get_logger
from src.graph.edges import route_after_router
from src.graph.nodes import clarify_node, generate_node, off_topic_node, router_node
from src.graph.state import ChatState

if TYPE_CHECKING:
    from langgraph.checkpoint.base import BaseCheckpointSaver
    from langgraph.graph.state import CompiledStateGraph

logger = get_logger(__name__)


def build_chat_graph(
    checkpointer: BaseCheckpointSaver[Any] | None = None,
) -> CompiledStateGraph[Any]:
    """
    Построить и скомпилировать граф чата.

    Структура графа:
        START → router ──┬─→ generate → END
                        ├─→ clarify  → END
                        └─→ off_topic → END

    Args:
        checkpointer: Checkpointer для персистентности состояния.
                     Если None, состояние не сохраняется.

    Returns:
        Скомпилированный граф, готовый к использованию.
    """
    logger.info("Building chat graph")

    # Создаём StateGraph с ChatState
    builder = StateGraph(ChatState)

    # Добавляем узлы
    builder.add_node("router", router_node)
    builder.add_node("generate", generate_node)
    builder.add_node("clarify", clarify_node)
    builder.add_node("off_topic", off_topic_node)

    # Добавляем рёбра
    # START -> router
    builder.add_edge(START, "router")

    # router -> conditional edge
    builder.add_conditional_edges(
        "router",
        route_after_router,
        {
            "generate": "generate",
            "clarify": "clarify",
            "off_topic": "off_topic",
        },
    )

    # Все конечные узлы -> END
    builder.add_edge("generate", END)
    builder.add_edge("clarify", END)
    builder.add_edge("off_topic", END)

    # Компилируем граф
    graph = builder.compile(checkpointer=checkpointer)

    logger.info(
        "Chat graph built",
        extra={"has_checkpointer": checkpointer is not None},
    )

    return graph
