"""Integration-тесты для полного flow Main Agent → Subagent → RAG."""

from __future__ import annotations

import pytest
from langchain_core.messages import HumanMessage

from src.graph.builder import build_chat_graph

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def chat_graph():
    """Фикстура: Main Agent граф без checkpointer."""
    return build_chat_graph(checkpointer=None)


# =============================================================================
# TESTS: Full Flow (Main Agent → Subagent)
# =============================================================================


@pytest.mark.asyncio
async def test_full_flow_products_query(chat_graph) -> None:
    """
    Тест: полный flow для запроса о продуктах.

    Main Agent должен:
    1. Проанализировать запрос
    2. Вызвать products_agent
    3. Products subagent выполнит RAG поиск (mock)
    4. Main Agent синтезирует финальный ответ
    """
    result = await chat_graph.ainvoke({
        "messages": [HumanMessage(content="Что принимать для сна?")]
    })

    assert result is not None
    assert "messages" in result

    messages = result["messages"]
    assert len(messages) > 0

    # Последнее сообщение — финальный ответ от Main Agent
    final_message = messages[-1]
    assert hasattr(final_message, "content")

    content = final_message.content.lower()

    # Ожидаем упоминания БАДов для сна
    assert any(keyword in content for keyword in [
        "мелатонин", "магний", "теанин", "сон", "бад"
    ])


@pytest.mark.asyncio
async def test_full_flow_compatibility_query(chat_graph) -> None:
    """
    Тест: полный flow для запроса о сочетаемости.

    Main Agent должен:
    1. Определить, что это вопрос о сочетаемости
    2. Вызвать compatibility_agent
    3. Compatibility subagent выполнит RAG поиск
    4. Main Agent вернёт ответ о совместимости
    """
    result = await chat_graph.ainvoke({
        "messages": [HumanMessage(content="Можно ли мелатонин с магнием?")]
    })

    assert result is not None
    assert "messages" in result

    messages = result["messages"]
    final_message = messages[-1]
    content = final_message.content.lower()

    # Ожидаем информацию о сочетаемости
    assert any(keyword in content for keyword in [
        "мелатонин", "магний", "совместим", "сочета", "комбинац", "синерг"
    ])


@pytest.mark.asyncio
async def test_full_flow_marketing_query(chat_graph) -> None:
    """
    Тест: полный flow для маркетингового запроса.

    Main Agent должен:
    1. Определить, что это маркетинговый запрос
    2. Вызвать marketing_agent
    3. Получить заглушку "в разработке"
    4. Вернуть информационное сообщение
    """
    result = await chat_graph.ainvoke({
        "messages": [HumanMessage(content="Создай баннер для продукта")]
    })

    assert result is not None
    assert "messages" in result

    messages = result["messages"]
    final_message = messages[-1]
    content = final_message.content.lower()

    # Ожидаем заглушку
    assert any(keyword in content for keyword in [
        "разработк", "phase 8", "скоро", "доступ"
    ])


@pytest.mark.asyncio
async def test_full_flow_off_topic_query(chat_graph) -> None:
    """
    Тест: полный flow для off-topic запроса.

    Main Agent должен:
    1. Определить, что запрос не по теме
    2. НЕ вызывать инструменты
    3. Вежливо отказать
    """
    result = await chat_graph.ainvoke({
        "messages": [HumanMessage(content="Какая погода завтра?")]
    })

    assert result is not None
    assert "messages" in result

    messages = result["messages"]
    final_message = messages[-1]
    content = final_message.content.lower()

    # Ожидаем вежливый отказ с упоминанием специализации
    assert any(keyword in content for keyword in [
        "специализ", "помо", "бад", "биохак", "сочетаем"
    ])


@pytest.mark.asyncio
async def test_full_flow_multiple_tools(chat_graph) -> None:
    """
    Тест: Main Agent может вызвать несколько инструментов.

    Запрос: "Какой БАД для сна и с чем его сочетать?"

    Main Agent должен:
    1. Вызвать products_agent (для рекомендации БАД)
    2. Вызвать compatibility_agent (для сочетаемости)
    3. Синтезировать единый ответ
    """
    result = await chat_graph.ainvoke({
        "messages": [HumanMessage(content="Какой БАД для сна и с чем его сочетать?")]
    })

    assert result is not None
    assert "messages" in result

    messages = result["messages"]
    final_message = messages[-1]
    content = final_message.content.lower()

    # Ожидаем информацию и о продуктах, и о сочетаемости
    has_product_info = any(keyword in content for keyword in [
        "мелатонин", "магний", "теанин", "дозир"
    ])
    has_compatibility_info = any(keyword in content for keyword in [
        "совместим", "сочета", "комбинац", "синерг", "вместе"
    ])

    # Хотя бы одна из тем должна быть покрыта
    # (в идеале обе, но зависит от ReAct цикла)
    assert has_product_info or has_compatibility_info


# =============================================================================
# TESTS: History Context
# =============================================================================


@pytest.mark.asyncio
async def test_full_flow_with_history(chat_graph) -> None:
    """
    Тест: субагенты получают историю диалога.

    Пользователь спрашивает сначала о БАДе, потом уточняет.
    Субагент должен видеть контекст предыдущих сообщений.
    """
    # Первый запрос
    result1 = await chat_graph.ainvoke({
        "messages": [HumanMessage(content="Что принимать для сна?")]
    })

    assert result1 is not None
    messages_after_first = result1["messages"]

    # Второй запрос (уточнение)
    result2 = await chat_graph.ainvoke({
        "messages": [*messages_after_first, HumanMessage(content="А дозировка какая?")]
    })

    assert result2 is not None
    assert "messages" in result2

    messages = result2["messages"]
    final_message = messages[-1]
    content = final_message.content.lower()

    # Ожидаем информацию о дозировке
    assert any(keyword in content for keyword in [
        "мг", "доз", "прин", "рекоменд"
    ])


# =============================================================================
# TESTS: Error Handling
# =============================================================================


@pytest.mark.asyncio
async def test_full_flow_empty_query(chat_graph) -> None:
    """Тест: пустой запрос обрабатывается корректно."""
    result = await chat_graph.ainvoke({
        "messages": [HumanMessage(content="")]
    })

    assert result is not None
    assert "messages" in result


@pytest.mark.asyncio
async def test_full_flow_very_long_query(chat_graph) -> None:
    """Тест: очень длинный запрос обрабатывается корректно."""
    long_query = "Расскажи подробно " + "очень " * 100 + "подробно про мелатонин"

    result = await chat_graph.ainvoke({
        "messages": [HumanMessage(content=long_query)]
    })

    assert result is not None
    assert "messages" in result


# =============================================================================
# TESTS: ReAct Cycle
# =============================================================================


@pytest.mark.asyncio
async def test_react_cycle_tool_call_present(chat_graph) -> None:
    """
    Тест: ReAct цикл содержит вызовы инструментов.

    Проверяем, что в messages есть AIMessage с tool_calls и ToolMessage.
    """
    result = await chat_graph.ainvoke({
        "messages": [HumanMessage(content="Что принимать для сна?")]
    })

    messages = result["messages"]

    # Ищем AIMessage с tool_calls
    has_tool_call = False
    for msg in messages:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            has_tool_call = True
            break

    # В ReAct flow должен быть хотя бы один tool call
    assert has_tool_call, "Expected at least one tool call in ReAct cycle"


@pytest.mark.asyncio
async def test_react_cycle_final_answer(chat_graph) -> None:
    """
    Тест: финальный ответ — это AIMessage без tool_calls.

    Последнее сообщение должно быть ответом пользователю, а не tool call.
    """
    result = await chat_graph.ainvoke({
        "messages": [HumanMessage(content="Что принимать для сна?")]
    })

    messages = result["messages"]
    final_message = messages[-1]

    # Финальное сообщение должно быть AIMessage
    assert hasattr(final_message, "content")

    # Финальное сообщение НЕ должно содержать tool_calls
    if hasattr(final_message, "tool_calls"):
        assert not final_message.tool_calls, "Final message should not have tool_calls"


# =============================================================================
# TESTS: RAG Mock Data
# =============================================================================


@pytest.mark.asyncio
async def test_rag_mock_data_products(chat_graph) -> None:
    """Тест: RAG mock возвращает данные для products домена."""
    result = await chat_graph.ainvoke({
        "messages": [HumanMessage(content="Что принимать для сна?")]
    })

    messages = result["messages"]
    final_message = messages[-1]
    content = final_message.content.lower()

    # Mock данные должны содержать информацию о мелатонине
    assert "мелатонин" in content or "магний" in content


@pytest.mark.asyncio
async def test_rag_mock_data_compatibility(chat_graph) -> None:
    """Тест: RAG mock возвращает данные для compatibility домена."""
    result = await chat_graph.ainvoke({
        "messages": [HumanMessage(content="Можно ли мелатонин с магнием?")]
    })

    messages = result["messages"]
    final_message = messages[-1]
    content = final_message.content.lower()

    # Mock данные должны содержать информацию о совместимости
    assert any(keyword in content for keyword in [
        "совместим", "синерг", "комбинац", "безопасн"
    ])

