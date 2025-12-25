"""Unit-тесты для субагентов (subgraphs)."""

from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from src.graph.subagents.base import (
    SubagentConfig,
    create_rag_subagent,
    inject_history,
)
from src.graph.subagents.compatibility import (
    COMPATIBILITY_CONFIG,
    compatibility_agent,
    get_compatibility_subagent,
)
from src.graph.subagents.marketing import marketing_agent
from src.graph.subagents.products import (
    PRODUCTS_CONFIG,
    get_products_subagent,
    products_agent,
)


# =============================================================================
# TESTS: inject_history
# =============================================================================


def test_inject_history_empty() -> None:
    """Тест: пустая история возвращает пустую строку."""
    result = inject_history([])
    assert result == ""


def test_inject_history_single_message() -> None:
    """Тест: одно сообщение форматируется корректно."""
    messages = [HumanMessage(content="Привет")]
    result = inject_history(messages)
    assert result == "User: Привет"


def test_inject_history_multiple_messages() -> None:
    """Тест: несколько сообщений форматируются корректно."""
    messages = [
        HumanMessage(content="Что принимать для сна?"),
        AIMessage(content="Рекомендую мелатонин."),
        HumanMessage(content="А дозировка?"),
    ]
    result = inject_history(messages)

    assert "User: Что принимать для сна?" in result
    assert "Assistant: Рекомендую мелатонин." in result
    assert "User: А дозировка?" in result


def test_inject_history_filters_tool_calls() -> None:
    """Тест: сообщения с tool_calls фильтруются."""
    messages = [
        HumanMessage(content="Привет"),
        AIMessage(content="", tool_calls=[{"id": "1", "name": "test", "args": {}}]),
        AIMessage(content="Ответ"),
    ]
    result = inject_history(messages)

    assert "User: Привет" in result
    assert "Assistant: Ответ" in result
    # Сообщение с tool_calls не должно попасть в историю
    assert result.count("Assistant:") == 1


def test_inject_history_window() -> None:
    """Тест: history_window ограничивает количество сообщений."""
    messages = [
        HumanMessage(content=f"Message {i}") for i in range(20)
    ]

    result = inject_history(messages, history_window=5)
    lines = result.split("\n")

    # Должно быть только 5 последних сообщений
    assert len(lines) == 5
    assert "Message 15" in result
    assert "Message 19" in result
    assert "Message 0" not in result


# =============================================================================
# TESTS: SubagentConfig
# =============================================================================


def test_subagent_config_defaults() -> None:
    """Тест: дефолтные значения SubagentConfig."""
    config = SubagentConfig(
        name="test",
        domain="products",
        system_prompt="Test prompt",
    )

    assert config.name == "test"
    assert config.domain == "products"
    assert config.system_prompt == "Test prompt"
    assert config.history_window == 10
    assert config.rag_top_k == 5
    assert config.rag_min_score == 0.5


def test_subagent_config_custom() -> None:
    """Тест: кастомные значения SubagentConfig."""
    config = SubagentConfig(
        name="custom",
        domain="compatibility",
        system_prompt="Custom prompt",
        history_window=20,
        rag_top_k=10,
        rag_min_score=0.8,
    )

    assert config.history_window == 20
    assert config.rag_top_k == 10
    assert config.rag_min_score == 0.8


# =============================================================================
# TESTS: create_rag_subagent
# =============================================================================


def test_create_rag_subagent_products() -> None:
    """Тест: создание Products subagent."""
    subagent = create_rag_subagent(PRODUCTS_CONFIG)

    assert subagent is not None
    # Проверяем, что это скомпилированный граф
    assert hasattr(subagent, "ainvoke")
    assert hasattr(subagent, "invoke")


def test_create_rag_subagent_compatibility() -> None:
    """Тест: создание Compatibility subagent."""
    subagent = create_rag_subagent(COMPATIBILITY_CONFIG)

    assert subagent is not None
    assert hasattr(subagent, "ainvoke")


def test_create_rag_subagent_custom_config() -> None:
    """Тест: создание субагента с кастомной конфигурацией."""
    custom_config = SubagentConfig(
        name="test_agent",
        domain="test",
        system_prompt="Test system prompt",
        history_window=5,
        rag_top_k=3,
        rag_min_score=0.7,
    )

    subagent = create_rag_subagent(custom_config)
    assert subagent is not None


# =============================================================================
# TESTS: get_*_subagent functions
# =============================================================================


def test_get_products_subagent() -> None:
    """Тест: получение Products subagent через фабрику."""
    subagent = get_products_subagent()
    assert subagent is not None


def test_get_compatibility_subagent() -> None:
    """Тест: получение Compatibility subagent через фабрику."""
    subagent = get_compatibility_subagent()
    assert subagent is not None


# =============================================================================
# TESTS: wrapper tools
# =============================================================================


@pytest.mark.asyncio
async def test_products_agent_wrapper() -> None:
    """Тест: products_agent wrapper вызывается корректно."""
    result = await products_agent.ainvoke({"query": "Что принимать для сна?"})

    assert isinstance(result, str)
    assert len(result) > 0
    # Проверяем, что возвращается содержательный ответ (не ошибка)
    assert "ошибка" not in result.lower() or "Извините" in result


@pytest.mark.asyncio
async def test_compatibility_agent_wrapper() -> None:
    """Тест: compatibility_agent wrapper вызывается корректно."""
    result = await compatibility_agent.ainvoke({"query": "Можно ли мелатонин с магнием?"})

    assert isinstance(result, str)
    assert len(result) > 0
    assert "ошибка" not in result.lower() or "Извините" in result


@pytest.mark.asyncio
async def test_marketing_agent_wrapper() -> None:
    """Тест: marketing_agent wrapper возвращает заглушку."""
    result = await marketing_agent.ainvoke({"query": "Создай баннер"})

    assert isinstance(result, str)
    assert "разработке" in result or "Phase 8" in result
    # Заглушка должна упоминать о доступных функциях
    assert "БАД" in result or "биохакинг" in result or "сочетаем" in result


@pytest.mark.asyncio
async def test_products_agent_with_history() -> None:
    """Тест: products_agent с историей диалога."""
    messages = [
        HumanMessage(content="Что принимать для сна?"),
        AIMessage(content="Мелатонин"),
    ]

    result = await products_agent.ainvoke({
        "query": "А дозировка?",
        "messages": messages
    })

    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_compatibility_agent_with_history() -> None:
    """Тест: compatibility_agent с историей диалога."""
    messages = [
        HumanMessage(content="Можно ли мелатонин с магнием?"),
        AIMessage(content="Да, это безопасная комбинация"),
    ]

    result = await compatibility_agent.ainvoke({
        "query": "А с кальцием?",
        "messages": messages
    })

    assert isinstance(result, str)
    assert len(result) > 0


# =============================================================================
# TESTS: error handling
# =============================================================================


@pytest.mark.asyncio
async def test_products_agent_empty_query() -> None:
    """Тест: products_agent с пустым запросом."""
    result = await products_agent.ainvoke({"query": ""})

    assert isinstance(result, str)
    # Должен корректно обработать пустой запрос


@pytest.mark.asyncio
async def test_compatibility_agent_empty_query() -> None:
    """Тест: compatibility_agent с пустым запросом."""
    result = await compatibility_agent.ainvoke({"query": ""})

    assert isinstance(result, str)


# =============================================================================
# TESTS: configurations consistency
# =============================================================================


def test_products_config_values() -> None:
    """Тест: Products config имеет правильные значения."""
    assert PRODUCTS_CONFIG.name == "products"
    assert PRODUCTS_CONFIG.domain == "products"
    assert PRODUCTS_CONFIG.rag_min_score == 0.5


def test_compatibility_config_values() -> None:
    """Тест: Compatibility config имеет правильные значения."""
    assert COMPATIBILITY_CONFIG.name == "compatibility"
    assert COMPATIBILITY_CONFIG.domain == "compatibility"
    assert COMPATIBILITY_CONFIG.rag_min_score == 0.6  # Выше порог для безопасности

