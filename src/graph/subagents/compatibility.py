"""Compatibility Subagent — эксперт по сочетаемости БАДов.

Это полноценный ReAct граф с:
- Доступом к истории диалога
- RAG поиском в домене 'compatibility'
- Query Planning через LLM
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from langchain_core.messages import AIMessage
from langchain_core.tools import tool

from src.core.logging import get_logger
from src.graph.prompts import COMPATIBILITY_SUBAGENT_SYSTEM_PROMPT

from .base import SubagentConfig, create_rag_subagent, inject_history

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph

logger = get_logger(__name__)


# =============================================================================
# SUBAGENT CONFIGURATION
# =============================================================================

COMPATIBILITY_CONFIG = SubagentConfig(
    name="compatibility",
    domain="compatibility",
    system_prompt=COMPATIBILITY_SUBAGENT_SYSTEM_PROMPT,
    history_window=10,
    rag_min_score=0.3,  # Понижен (было 0.6, слишком строго)
    rag_top_k_per_query=5,  # Сколько результатов на каждый подзапрос
    rag_final_top_k=15,  # Итого чанков после merge всех подзапросов
)


# =============================================================================
# SUBAGENT GRAPH
# =============================================================================


def get_compatibility_subagent() -> CompiledStateGraph[Any]:
    """
    Получить Compatibility subagent граф.

    Returns:
        Скомпилированный ReAct граф субагента.
    """
    return create_rag_subagent(COMPATIBILITY_CONFIG)


# =============================================================================
# WRAPPER TOOL для Main Agent
# =============================================================================


@tool
async def compatibility_agent(query: str, messages: list[Any] | None = None) -> str:
    """
    Агент по сочетаемости: анализ совместимости БАДов и добавок между собой.

    Вызывай этот инструмент когда пользователь спрашивает про:
    - Можно ли комбинировать определённые БАДы
    - Какие добавки усиливают действие друг друга
    - Какие сочетания опасны или нежелательны
    - Взаимодействие добавок между собой
    - Рекомендации по комбинированию для достижения цели

    Args:
        query: Вопрос о сочетаемости продуктов.
        messages: История диалога (автоматически инжектится через InjectedState).

    Returns:
        Анализ сочетаемости от специалиста с RAG поиском.
    """
    logger.info(
        "Compatibility agent wrapper called",
        extra={
            "query_preview": query[:100] if query else "empty",
            "has_history": messages is not None and len(messages) > 0,
        },
    )

    try:
        # Получаем субагент
        subagent = get_compatibility_subagent()

        # Формируем историю для контекста (если есть)
        history_context = ""
        if messages:
            history_context = inject_history(
                messages, COMPATIBILITY_CONFIG.history_window
            )

        # Формируем полный запрос с историей
        full_query = query
        if history_context:
            full_query = (
                f"История диалога:\n{history_context}\n\nТекущий вопрос: {query}"
            )

        # Вызываем субагент
        result = await subagent.ainvoke(
            {"messages": [{"role": "user", "content": full_query}]}
        )

        # Извлекаем ответ из результата
        if result and "messages" in result:
            messages_result = result["messages"]
            if messages_result:
                last_message = messages_result[-1]
                if isinstance(last_message, AIMessage):
                    response = str(last_message.content)
                else:
                    response = str(last_message)

                logger.info(
                    "Compatibility agent completed",
                    extra={"response_length": len(response)},
                )
                return response

        # Fallback если что-то пошло не так
        logger.warning("Compatibility agent returned empty result")
        return "Извините, не удалось получить информацию о сочетаемости."

    except Exception as e:
        logger.error(
            "Compatibility agent failed",
            extra={"error": str(e), "query": query[:100]},
        )
        return f"Произошла ошибка при поиске информации: {e!s}"
