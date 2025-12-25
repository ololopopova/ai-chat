"""Сборка ReAct Main Agent графа."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from langgraph.prebuilt import create_react_agent

from src.core.logging import get_logger
from src.graph.prompts import MAIN_AGENT_SYSTEM_PROMPT
from src.graph.subagents import compatibility_agent, marketing_agent, products_agent
from src.llm import get_llm_provider

if TYPE_CHECKING:
    from langgraph.checkpoint.base import BaseCheckpointSaver
    from langgraph.graph.state import CompiledStateGraph

logger = get_logger(__name__)


def build_chat_graph(
    checkpointer: BaseCheckpointSaver[Any] | None = None,
) -> CompiledStateGraph[Any]:
    """
    Построить и скомпилировать ReAct Main Agent граф.

    Новая архитектура:
        START → main_agent (ReAct loop) → END
                     ↓
            tools (при необходимости):
            - products_agent
            - compatibility_agent
            - marketing_agent

    Main Agent — это интеллектуальный ReAct агент, который:
    1. Анализирует запрос пользователя
    2. Решает какие инструменты (субагенты) нужно вызвать
    3. Вызывает один или несколько инструментов
    4. Синтезирует финальный ответ на основе полученных данных
    5. Или отвечает напрямую если инструменты не нужны (например, off-topic)

    Args:
        checkpointer: Checkpointer для персистентности состояния.
                     Если None, состояние не сохраняется между вызовами.

    Returns:
        Скомпилированный ReAct граф, готовый к использованию.

    Example:
        >>> graph = build_chat_graph()
        >>> result = await graph.ainvoke({
        ...     "messages": [{"role": "user", "content": "Что принимать для сна?"}]
        ... })
    """
    logger.info("Building ReAct Main Agent graph")

    # Получаем LLM провайдер
    provider = get_llm_provider()
    llm = provider.model  # MockChatModel теперь SimpleChatModel (BaseChatModel)

    # Список инструментов (субагентов) доступных Main Agent
    tools = [
        products_agent,
        compatibility_agent,
        marketing_agent,
    ]

    logger.debug(
        "Registered tools",
        extra={
            "tools": [tool.name for tool in tools],
            "count": len(tools),
        },
    )

    # Создаём ReAct агента с инструментами
    # create_react_agent автоматически:
    # - Создаёт граф с циклом: думай → действуй → наблюдай → думай
    # - Управляет вызовами tools
    # - Обрабатывает ToolMessage
    # - Формирует финальный ответ
    #
    # System prompt передаётся через параметр prompt (строка или SystemMessage)
    graph = create_react_agent(
        model=llm,
        tools=tools,
        prompt=MAIN_AGENT_SYSTEM_PROMPT,  # ✅ Правильный способ!
        checkpointer=checkpointer,
    )

    logger.info(
        "ReAct Main Agent graph built successfully",
        extra={
            "has_checkpointer": checkpointer is not None,
            "tools_count": len(tools),
        },
    )

    return graph
