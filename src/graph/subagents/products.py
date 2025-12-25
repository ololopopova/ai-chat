"""Products Subagent — эксперт по БАДам и биохакингу.

Это полноценный ReAct граф с:
- Доступом к истории диалога
- RAG поиском в домене 'products'
- Query Planning через LLM
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from langchain_core.messages import AIMessage
from langchain_core.tools import tool

from src.core.logging import get_logger
from src.graph.prompts import PRODUCTS_SUBAGENT_SYSTEM_PROMPT

from .base import SubagentConfig, create_rag_subagent, inject_history

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph

logger = get_logger(__name__)


# =============================================================================
# SUBAGENT CONFIGURATION
# =============================================================================

PRODUCTS_CONFIG = SubagentConfig(
    name="products",
    domain="products",
    system_prompt=PRODUCTS_SUBAGENT_SYSTEM_PROMPT,
    history_window=10,
    rag_min_score=0.3,  # Понижен для лучшего recall
    rag_top_k_per_query=5,  # Сколько результатов на каждый подзапрос
    rag_final_top_k=15,  # Итого чанков после merge всех подзапросов
)


# =============================================================================
# SUBAGENT GRAPH
# =============================================================================

def get_products_subagent() -> CompiledStateGraph[Any]:
    """
    Получить Products subagent граф.

    Returns:
        Скомпилированный ReAct граф субагента.
    """
    return create_rag_subagent(PRODUCTS_CONFIG)


# =============================================================================
# WRAPPER TOOL для Main Agent
# =============================================================================

@tool
async def products_agent(query: str, messages: list[Any] | None = None) -> str:
    """
    Агент по продуктам: БАДы, микродозинг грибов, биохакинг, рецепты и привычки.

    Вызывай этот инструмент когда пользователь спрашивает про:
    - Конкретные БАДы и добавки
    - Дозировки и схемы приёма
    - Микродозинг грибов
    - Курс биохакинга
    - Рецепты и здоровые привычки
    - Рекомендации по продуктам для конкретных целей

    Args:
        query: Вопрос пользователя или уточненный запрос.
        messages: История диалога (автоматически инжектится через InjectedState).

    Returns:
        Информация о продуктах от специалиста с RAG поиском.
    """
    logger.info(
        "Products agent wrapper called",
        extra={
            "query_preview": query[:100] if query else "empty",
            "has_history": messages is not None and len(messages) > 0,
        },
    )

    try:
        # Получаем субагент
        subagent = get_products_subagent()

        # Формируем историю для контекста (если есть)
        history_context = ""
        if messages:
            history_context = inject_history(messages, PRODUCTS_CONFIG.history_window)

        # Формируем полный запрос с историей
        full_query = query
        if history_context:
            full_query = f"История диалога:\n{history_context}\n\nТекущий вопрос: {query}"

        # Вызываем субагент
        result = await subagent.ainvoke({
            "messages": [{"role": "user", "content": full_query}]
        })

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
                    "Products agent completed",
                    extra={"response_length": len(response)},
                )
                return response

        # Fallback если что-то пошло не так
        logger.warning("Products agent returned empty result")
        return "Извините, не удалось получить информацию о продуктах."

    except Exception as e:
        logger.error(
            "Products agent failed",
            extra={"error": str(e), "query": query[:100]},
        )
        return f"Произошла ошибка при поиске информации: {e!s}"

