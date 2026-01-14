"""Базовая инфраструктура для субагентов с RAG и InjectedState.

Субагент — это полноценный ReAct граф с:
- Доступом к истории диалога через InjectedState
- Своим LLM для Query Planning
- MCP tools для RAG поиска
- Возможностью масштабирования
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from src.core.logging import get_logger
from src.llm import get_llm_provider

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel
    from langgraph.graph.state import CompiledStateGraph

logger = get_logger(__name__)


@dataclass
class SubagentConfig:
    """
    Конфигурация субагента.

    Attributes:
        name: Имя субагента (для логирования).
        domain: Домен для RAG поиска (products, compatibility).
        system_prompt: Системный промпт субагента.
        history_window: Количество последних сообщений для контекста.
        rag_min_score: Минимальный порог релевантности.
        rag_top_k_per_query: Сколько результатов брать на каждый подзапрос.
        rag_final_top_k: Итоговое количество результатов после merge.
    """

    name: str
    domain: str
    system_prompt: str
    history_window: int = 10
    rag_min_score: float = 0.3
    rag_top_k_per_query: int = 5
    rag_final_top_k: int = 15


def inject_history(
    messages: list[Any],
    history_window: int = 10,
) -> str:
    """
    Извлечь историю диалога из messages и форматировать для LLM.

    Args:
        messages: Список сообщений из state.
        history_window: Количество последних сообщений.

    Returns:
        Форматированная история диалога.
    """
    if not messages:
        return ""

    # Берём последние N сообщений
    recent_messages = messages[-history_window:]

    history_parts: list[str] = []

    for msg in recent_messages:
        # Обрабатываем разные типы сообщений
        if isinstance(msg, HumanMessage):
            history_parts.append(f"User: {msg.content}")
        elif isinstance(msg, AIMessage) and not msg.tool_calls:
            # Пропускаем технические сообщения с tool_calls
            history_parts.append(f"Assistant: {msg.content}")
        # SystemMessage и ToolMessage пропускаем

    if not history_parts:
        return ""

    return "\n".join(history_parts)


def create_rag_subagent(
    config: SubagentConfig,
    llm: BaseChatModel | None = None,
) -> CompiledStateGraph[Any]:
    """
    Создать ReAct субагент с RAG инструментами.

    Args:
        config: Конфигурация субагента.
        llm: LLM модель (если None, используется дефолтная).

    Returns:
        Скомпилированный ReAct граф субагента.

    Example:
        >>> config = SubagentConfig(
        ...     name="products",
        ...     domain="products",
        ...     system_prompt=PRODUCTS_SUBAGENT_SYSTEM_PROMPT,
        ... )
        >>> subagent = create_rag_subagent(config)
    """
    logger.info(
        "Creating RAG subagent",
        extra={
            "subagent_name": config.name,
            "domain": config.domain,
            "history_window": config.history_window,
        },
    )

    # Получаем LLM
    if llm is None:
        provider = get_llm_provider()
        llm = provider.model

    # Создаём RAG tool для этого субагента
    rag_tool = _create_rag_tool(config)

    # Создаём ReAct агента
    # В Phase 6 используем простой tool без реального MCP
    # В следующих фазах здесь будет полноценный MCP client
    subagent = create_react_agent(
        model=llm,
        tools=[rag_tool],
        prompt=config.system_prompt,  # System prompt субагента
    )

    logger.info(
        "RAG subagent created",
        extra={"subagent_name": config.name},
    )

    return subagent


def _create_rag_tool(config: SubagentConfig) -> Any:
    """
    Создать RAG tool для субагента через MCP.

    Использует MCP client для вызова hybrid_search tool через протокол MCP.
    Поддерживает stdio и HTTP транспорты.

    Args:
        config: Конфигурация субагента.

    Returns:
        LangChain tool для RAG поиска через MCP.
    """

    @tool
    async def rag_hybrid_search(
        vector_queries: list[str],
        fts_keywords: list[str],
    ) -> str:
        """
        Множественный гибридный поиск через MCP с reranking.

        Args:
            vector_queries: 2-3 подзапроса для семантического поиска.
            fts_keywords: 5-7 ключевых слов для полнотекстового поиска.

        Returns:
            Форматированный контекст из базы знаний.
        """
        logger.info(
            "RAG MCP tool called",
            extra={
                "domain": config.domain,
                "vector_queries": vector_queries,
                "fts_keywords": fts_keywords,
            },
        )

        try:
            # Получаем MCP client
            from src.mcp_client import get_mcp_client

            mcp_client = get_mcp_client()

            if mcp_client is None or not mcp_client.is_initialized:
                # MCP client не инициализирован — возвращаем ошибку
                logger.error(
                    "MCP client not available",
                    extra={"domain": config.domain},
                )
                return "❌ MCP сервер недоступен. Попробуйте позже."

            # Получаем tool из MCP client
            mcp_tool = await mcp_client.get_tool_by_name("hybrid_search")

            if mcp_tool is None:
                logger.error(
                    "hybrid_search tool not found in MCP",
                    extra={"domain": config.domain},
                )
                return "❌ Инструмент поиска недоступен."

            # Вызываем MCP tool
            result = await mcp_tool.ainvoke(
                {
                    "vector_queries": vector_queries,
                    "fts_keywords": fts_keywords,
                    "domain": config.domain,
                    "top_k_per_query": config.rag_top_k_per_query,
                    "final_top_k": config.rag_final_top_k,
                    "min_score": config.rag_min_score,
                    "use_reranker": True,
                }
            )

            # MCP tool может возвращать:
            # - str (текст напрямую)
            # - list[dict] с {"type": "text", "text": "..."}
            if isinstance(result, list):
                # Извлекаем текст из MCP формата
                texts = []
                for item in result:
                    if isinstance(item, dict) and "text" in item:
                        texts.append(item["text"])
                    elif isinstance(item, str):
                        texts.append(item)
                result_text = "\n".join(texts)
            else:
                result_text = str(result) if result else ""

            logger.info(
                "MCP hybrid_search completed",
                extra={
                    "domain": config.domain,
                    "result_length": len(result_text),
                },
            )

            # Проверяем результат
            if not result_text or result_text.strip() == "":
                logger.warning(
                    "No results found via MCP",
                    extra={
                        "domain": config.domain,
                        "vector_queries": vector_queries,
                        "fts_keywords": fts_keywords,
                    },
                )
                return (
                    "❌ Информация не найдена в базе знаний. Попробуйте переформулировать запрос."
                )

            return result_text

        except Exception as e:
            logger.error(
                "MCP tool failed",
                extra={
                    "domain": config.domain,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            return f"❌ Ошибка при поиске в базе знаний: {e}"

    # Устанавливаем правильное имя для tool
    rag_hybrid_search.name = "rag_hybrid_search"
    rag_hybrid_search.description = f"MCP hybrid search с reranking для домена '{config.domain}'"

    return rag_hybrid_search
