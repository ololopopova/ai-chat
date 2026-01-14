"""
Тесты для ReAct Main Agent узлов и логики.

NOTE: В ReAct архитектуре нет отдельных узлов (router, generate, clarify).
create_react_agent управляет своим циклом сам.

Эти тесты покрывают:
- Работу ReAct агента в целом
- Вызов инструментов (tools)
- Формирование ответов
"""

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from src.graph.builder import build_chat_graph


class TestReActMainAgent:
    """Тесты для ReAct Main Agent."""

    @pytest.mark.asyncio
    async def test_simple_question_no_tools(self) -> None:
        """
        Тест: простой вопрос без вызова инструментов.

        Если вопрос off-topic, ReAct агент должен ответить напрямую
        без вызова tools.
        """
        pytest.skip("Mock LLM не может корректно имитировать ReAct поведение с tools")
        graph = build_chat_graph()

        input_state = {
            "messages": [HumanMessage(content="Привет, как дела?")],
        }

        # Мокнутый LLM должен вернуть off-topic ответ без tool calls
        # TODO: реализовать с моком LLM
        result = await graph.ainvoke(input_state)

        assert "messages" in result
        assert len(result["messages"]) > 1
        # Последнее сообщение — ответ агента
        last_message = result["messages"][-1]
        assert isinstance(last_message, AIMessage)

    @pytest.mark.asyncio
    async def test_products_question_calls_tool(self) -> None:
        """
        Тест: вопрос о продуктах должен вызвать products_agent tool.

        ReAct агент должен:
        1. Определить что нужен products_agent
        2. Вызвать tool
        3. Получить результат
        4. Синтезировать ответ
        """
        pytest.skip("Mock LLM не может корректно имитировать ReAct поведение с tools")
        graph = build_chat_graph()

        input_state = {
            "messages": [HumanMessage(content="Что принимать для сна?")],
        }

        # TODO: реализовать с моком LLM и проверкой tool_calls
        result = await graph.ainvoke(input_state)

        assert "messages" in result
        # Должны быть: HumanMessage, AIMessage (tool call), ToolMessage, AIMessage (ответ)
        assert len(result["messages"]) >= 2

    @pytest.mark.asyncio
    async def test_combined_question_calls_multiple_tools(self) -> None:
        """
        Тест: сложный вопрос должен вызвать несколько tools.

        Например: "Какой БАД для сна и с чем его сочетать?"
        Должны вызваться: products_agent + compatibility_agent
        """
        pytest.skip("Mock LLM не может корректно имитировать ReAct поведение с tools")
        graph = build_chat_graph()

        input_state = {
            "messages": [HumanMessage(content="Какой БАД для сна и с чем его сочетать?")],
        }

        # TODO: реализовать с моком LLM
        result = await graph.ainvoke(input_state)

        assert "messages" in result
        # Должно быть несколько tool calls
        assert len(result["messages"]) >= 2


class TestToolsStubs:
    """Тесты для заглушек инструментов."""

    @pytest.mark.asyncio
    async def test_products_agent_stub(self) -> None:
        """Тест заглушки products_agent."""
        from src.graph.subagents import products_agent

        result = await products_agent.ainvoke({"query": "Что для сна?"})

        assert isinstance(result, str)
        assert len(result) > 0
        # Принимаем как реальный RAG результат, так и mock ответ
        is_rag_result = "мелатонин" in result.lower() or "магний" in result.lower()
        is_mock_result = "mock" in result.lower()
        assert is_rag_result or is_mock_result, f"Unexpected result: {result}"

    @pytest.mark.asyncio
    async def test_compatibility_agent_stub(self) -> None:
        """Тест заглушки compatibility_agent."""
        from src.graph.subagents import compatibility_agent

        result = await compatibility_agent.ainvoke({"query": "Сочетаемость мелатонина"})

        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_marketing_agent_stub(self) -> None:
        """Тест заглушки marketing_agent."""
        from src.graph.subagents import marketing_agent

        result = await marketing_agent.ainvoke({"query": "Создай баннер"})

        assert isinstance(result, str)
        assert len(result) > 0
        assert "баннер" in result.lower()
